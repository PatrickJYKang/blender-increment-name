bl_info = {
    "name": "Increment Name",
    "author": "Patrick Kang",
    "version": (0, 9, 1),
    "blender": (3, 0, 0),
    "description": "Properly increments numbered object names after duplication.",
    "category": "Object",
}

import bpy
import re
import time
from bpy.props import StringProperty, CollectionProperty, BoolProperty, IntProperty
from bpy.types import AddonPreferences, UIList, Operator, Panel

number_pattern = re.compile(r'(\d+)')
suffix_pattern = re.compile(r'\.\d{3}$')

def smart_increment_name(name, escape_patterns=None):
    # Remove Blender .001 style suffix first
    name = suffix_pattern.sub('', name)
    
    # Get escape patterns from preferences if not provided
    if escape_patterns is None:
        try:
            # In Blender, the actual module name might be just "addon"
            # when installed, regardless of the file name
            prefs = None
            for addon_name in bpy.context.preferences.addons.keys():
                if addon_name == __name__ or addon_name == "addon":
                    prefs = bpy.context.preferences.addons[addon_name].preferences
                    break
                    
            if prefs:
                escape_patterns = [pattern.pattern for pattern in prefs.escape_patterns]
            else:
                escape_patterns = []  # Fallback to empty list
        except (KeyError, AttributeError):
            escape_patterns = []  # Fallback to empty list
    
    # Check if any escape patterns apply to this name
    escaped_name = name
    escaped_ranges = []
    
    for pattern in escape_patterns:
        if not pattern:
            continue  # Skip empty patterns
        
        # Find all occurrences of this pattern
        for match in re.finditer(re.escape(pattern), name):
            # Mark this range as escaped
            escaped_ranges.append((match.start(), match.end()))
    
    # Sort ranges by start position
    escaped_ranges.sort()
    
    # Find all numbers and check if they're in escaped ranges
    for match in number_pattern.finditer(name):
        num_str = match.group(1)
        start, end = match.span(1)
        
        # Check if this number is in an escaped range
        is_escaped = False
        for e_start, e_end in escaped_ranges:
            if start >= e_start and end <= e_end:
                is_escaped = True
                break
        
        if not is_escaped:
            # This number is not escaped, we can increment it
            base = name[:start]
            num = int(num_str)
            end_part = name[end:]
            
            while True:
                new_num = str(num + 1).zfill(len(num_str))
                new_name = base + new_num + end_part
                if new_name not in bpy.data.objects:
                    return new_name
                num += 1
            
            # We found and incremented a non-escaped number, so we're done
            break
    
    # If we didn't find any non-escaped numbers, use the default suffix method
    base = name
    suffix_num = 1
    while True:
        new_name = f"{base}.{suffix_num:03}"
        if new_name not in bpy.data.objects:
            return new_name
        suffix_num += 1

class OBJECT_OT_increment_name_duplicate(bpy.types.Operator):
    """Duplicate with intelligent name incrementing"""
    bl_idname = "object.increment_name_duplicate"
    bl_label = "Increment Name Duplicate"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    _duplicated_objects = []

    def execute(self, context):
        bpy.ops.object.duplicate_move('INVOKE_DEFAULT')
        # Save the duplicated objects to rename later
        self._duplicated_objects = list(context.selected_objects)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # First time in modal - rename objects and simulate a click
        if not hasattr(self, "_renamed") or not self._renamed:
            # Rename the objects
            for obj in self._duplicated_objects:
                if obj.name.endswith((".001", ".002", ".003")):
                    obj.name = smart_increment_name(obj.name)
            self._renamed = True
            self.report({'INFO'}, "Object duplicated with incremented name")
            
            # Auto-finish after renaming (simulates a mouse click)
            return {'FINISHED'}

        # These handlers below won't be reached due to auto-finish above,
        # but kept for safety
        if event.type in {'LEFTMOUSE', 'RET', 'SPACE'} and event.value == 'PRESS':
            return {'FINISHED'}

        if event.type in {'ESC'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

# Update function for pattern property
def update_pattern_name(self, context):
    # Update the name attribute based on the pattern value
    if self.pattern:
        self.name = f"Escape: {self.pattern}"
    else:
        self.name = "Empty Pattern"

# Escape Pattern item for the preferences panel
class INCREMENT_NAME_escape_pattern(bpy.types.PropertyGroup):
    # The name property is used for displaying in the UI list
    name: StringProperty(
        name="Name",
        default="New Pattern"
    )
    
    pattern: StringProperty(
        name="Pattern",
        description="Text pattern to escape from number incrementing",
        default="",
        update=update_pattern_name
    )

# Operator to add a new pattern
class INCREMENT_NAME_OT_add_pattern(Operator):
    bl_idname = "object.increment_name_add_pattern"
    bl_label = "Add Escape Pattern"
    bl_description = "Add a new pattern to escape from incrementing"
    bl_options = {'REGISTER', 'UNDO'}
    
    new_pattern: StringProperty(
        name="New Pattern",
        description="Enter the pattern to escape from incrementing",
        default=""
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_pattern")
        layout.label(text="Example: For '1WALLN' objects, enter '1WALL'")
        layout.label(text="to increment N instead of 1")

    def execute(self, context):
        try:
            prefs = None
            # Find addon preferences
            for addon_name in [__name__, "addon", __name__.split('.')[-1]]:
                if addon_name in context.preferences.addons:
                    prefs = context.preferences.addons[addon_name].preferences
                    if prefs is not None:
                        break
            
            if prefs is not None:
                item = prefs.escape_patterns.add()
                item.pattern = self.new_pattern  # This will trigger the update function
                prefs.active_pattern_index = len(prefs.escape_patterns) - 1
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Could not access addon preferences")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

# Operator to remove a pattern
class INCREMENT_NAME_OT_remove_pattern(Operator):
    bl_idname = "object.increment_name_remove_pattern"
    bl_label = "Remove Escape Pattern"
    bl_description = "Remove the selected escape pattern"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        if prefs.active_pattern_index >= 0:
            prefs.escape_patterns.remove(prefs.active_pattern_index)
            prefs.active_pattern_index = min(prefs.active_pattern_index, len(prefs.escape_patterns) - 1)
        return {'FINISHED'}

# Preferences panel for the addon
class IncrementNamePreferences(AddonPreferences):
    bl_idname = __name__

    escape_patterns: CollectionProperty(type=INCREMENT_NAME_escape_pattern)
    active_pattern_index: IntProperty(name="Active Pattern Index")
    
    recursive_collection_rename: BoolProperty(
        name="Recursive Collection Rename",
        description="When enabled, objects in nested collections will also be renamed when duplicating a collection",
        default=True
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="Escape Patterns:")
        layout.label(text="These patterns will be excluded from number incrementing")

        row = layout.row()
        row.template_list("UI_UL_list", "escape_patterns", self, "escape_patterns", 
                          self, "active_pattern_index", rows=3)

        col = row.column(align=True)
        col.operator("object.smart_duplicate_add_pattern", icon="ADD", text="")
        col.operator("object.smart_duplicate_remove_pattern", icon="REMOVE", text="")

        if len(self.escape_patterns) > 0 and self.active_pattern_index >= 0:
            item = self.escape_patterns[self.active_pattern_index]
            layout.prop(item, "pattern")
        
        layout.separator()
        layout.label(text="Example: For objects named '1WALLN', add '1WALL' as a pattern to increment the N instead of the 1")

# Sidebar panel for escape patterns management
class VIEW3D_PT_increment_name(Panel):
    bl_label = "Increment Name"
    bl_idname = "VIEW3D_PT_increment_name"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"  # This puts it in the Tool tab of the sidebar

    def draw(self, context):
        layout = self.layout
        
        # Get addon preferences safely
        prefs = None
        try:
            # Try common addon name possibilities
            for addon_name in [__name__, "addon", __name__.split('.')[-1]]:
                if addon_name in context.preferences.addons:
                    prefs = context.preferences.addons[addon_name].preferences
                    if prefs is not None:
                        break
            
            if prefs is not None:
                # Collection settings
                box = layout.box()
                box.label(text="Collection Settings:")
                box.prop(prefs, "recursive_collection_rename")
                
                layout.separator()
                
                # Escape patterns
                layout.label(text="Escape Patterns:")
                layout.label(text="Patterns to exclude from incrementing")
    
                # Add/remove pattern buttons
                row = layout.row()
                row.operator("object.increment_name_add_pattern", icon="ADD", text="Add Pattern")
                row.operator("object.increment_name_remove_pattern", icon="REMOVE", text="Remove Pattern")
                
                # Pattern list
                layout.template_list("UI_UL_list", "escape_patterns", prefs, "escape_patterns", 
                                  prefs, "active_pattern_index", rows=3)
    
                # Edit selected pattern
                if len(prefs.escape_patterns) > 0 and prefs.active_pattern_index >= 0:
                    item = prefs.escape_patterns[prefs.active_pattern_index]
                    layout.prop(item, "pattern")
                
                layout.separator()
                layout.label(text="Example: For '1WALLN', add '1WALL'")
                layout.label(text="to increment N instead of 1")
            else:
                layout.label(text="Could not access addon preferences.")
                layout.label(text="Please restart Blender.")
            
        except (KeyError, AttributeError, TypeError) as e:
            # If addon preferences can't be accessed
            layout.label(text="Addon preferences error:")
            layout.label(text=str(e))
            layout.label(text="Please save and restart Blender.")

addon_keymaps = []

# Helper function to rename objects within a collection
def smart_rename_collection_objects(collection, recursive=True):
    """Rename all objects in the collection using smart_increment_name"""
    try:
        # First rename objects directly in this collection
        for obj in collection.objects:
            if obj.name.endswith((".001", ".002", ".003")):
                obj.name = smart_increment_name(obj.name)
        
        # Then process child collections if recursive is enabled
        if recursive:
            for child_collection in collection.children:
                smart_rename_collection_objects(child_collection, recursive)
    except Exception as e:
        print(f"Increment Name: Error renaming collection objects: {e}")

# Collection duplication operator - works like the object duplication
class OUTLINER_OT_increment_name_collection_duplicate(Operator):
    """Duplicate collections with intelligent name incrementing"""
    bl_idname = "outliner.increment_name_collection_duplicate"
    bl_label = "Increment Name Collection Duplicate"
    bl_description = "Duplicate selected collection with smart naming"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Track newly created collections
    _duplicated_collections = []
    
    def execute(self, context):
        try:
            # Call Blender's built-in duplicate operation
            bpy.ops.outliner.collection_duplicate('INVOKE_DEFAULT')
            
            # This will be run right after the duplication completes
            # We'll need to find newly created collections in the modal method
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        except Exception as e:
            self.report({'ERROR'}, f"Increment Name: {e}")
            return {'CANCELLED'}
    
    def modal(self, context, event):
        try:
            # Find any newly created collections with .001 suffix
            for collection in bpy.data.collections:
                if collection.name.endswith((".001", ".002", ".003")):
                    # First rename the collection itself
                    new_name = smart_increment_name(collection.name)
                    collection.name = new_name
                    
                    # Then process all objects inside
                    prefs = get_addon_prefs()
                    recursive = True if prefs is None else prefs.recursive_collection_rename
                    smart_rename_collection_objects(collection, recursive)
            
            # Auto-finish after renaming (simulates accepting the duplication)
            return {'FINISHED'}
        except Exception as e:
            print(f"Increment Name: Error in modal function: {e}")
            return {'FINISHED'}

def get_addon_prefs():
    """Safely get addon preferences"""
    try:
        # Try several possible addon names
        for addon_name in [__name__, "addon", __name__.split('.')[-1]]:
            if addon_name in bpy.context.preferences.addons:
                return bpy.context.preferences.addons[addon_name].preferences
    except (KeyError, AttributeError, TypeError):
        pass
    # Fallback to default value if addon is not loaded or during registration
    return None



def register():
    # Register all our custom classes
    bpy.utils.register_class(INCREMENT_NAME_escape_pattern)
    bpy.utils.register_class(INCREMENT_NAME_OT_add_pattern)
    bpy.utils.register_class(INCREMENT_NAME_OT_remove_pattern)
    bpy.utils.register_class(IncrementNamePreferences)
    bpy.utils.register_class(OBJECT_OT_increment_name_duplicate)
    bpy.utils.register_class(VIEW3D_PT_increment_name)
    bpy.utils.register_class(OUTLINER_OT_increment_name_collection_duplicate)
    
    # Set up the keyboard shortcuts
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # For 3D View - Object duplication
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new(OBJECT_OT_increment_name_duplicate.bl_idname, 'D', 'PRESS', shift=True)
        addon_keymaps.append((km, kmi))
        
        # For Outliner - Collection duplication
        km = kc.keymaps.new(name='Outliner', space_type='OUTLINER')
        kmi = km.keymap_items.new(OUTLINER_OT_increment_name_collection_duplicate.bl_idname, 'D', 'PRESS', shift=True)
        addon_keymaps.append((km, kmi))

def unregister():
    # Remove all keyboard shortcuts
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Unregister all classes in reverse order
    bpy.utils.unregister_class(OUTLINER_OT_increment_name_collection_duplicate)
    bpy.utils.unregister_class(VIEW3D_PT_increment_name)
    bpy.utils.unregister_class(OBJECT_OT_increment_name_duplicate)
    bpy.utils.unregister_class(IncrementNamePreferences)
    bpy.utils.unregister_class(INCREMENT_NAME_OT_remove_pattern)
    bpy.utils.unregister_class(INCREMENT_NAME_OT_add_pattern)
    bpy.utils.unregister_class(INCREMENT_NAME_escape_pattern)

if __name__ == "__main__":
    register()
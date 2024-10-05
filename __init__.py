    # Builtin Modules
import bpy
import bmesh
import math
import mathutils

bl_info = {
    "name": "Tidy Mesh",
    "blender": (4, 2, 1),
    "location": "Properties editor",
    "author": "Daniel Hong",
    "description": "Removes overlapping vertices and makes quad faces where applicable",
    "category": "3D View"
}

class TidyMeshOperator(bpy.types.Operator):
    """Tidy Mesh Operator"""
    bl_idname = "mesh.tidy_mesh"
    bl_label = "Tidy Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            self.tidy_mesh(context)
            return {'FINISHED'}
        else:
            print("Active object is not a mesh.")
            return {'CANCELLED'}

    def tidy_mesh(self, context):

        obj = context.active_object
        mesh = obj.data
        
        # Get the number of selected vertices before merging
        selected_verts_before = sum(1 for v in mesh.vertices if v.select)

        # Merge selected vertices by distance
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        
        # Merge adjacent faces
        self.handle_adjacent_faces(obj)

    def handle_adjacent_faces(self, obj):
        """Combine adjacent faces with the same normals into one face."""
        mesh = obj.data

        # Switch to object mode to apply changes
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Create a list to track merged faces
        merged_faces = set()

        for face in bm.faces:
            if face in merged_faces:
                continue  # Skip already merged faces

            # Get the normal of the current face
            face_normal = face.normal

            # Create a list to hold faces to be merged
            faces_to_merge = [face]

            # Check neighboring faces
            for edge in face.edges:
                for neighbor_face in edge.link_faces:
                    if neighbor_face != face and neighbor_face not in merged_faces:
                        # Compare the normals
                        if face_normal == neighbor_face.normal:
                            faces_to_merge.append(neighbor_face)

            # If there are exactly two faces to merge
            if len(faces_to_merge) == 2:
                new_verts = []  # List to collect vertices

                # Collect unique vertices from both faces
                for face in faces_to_merge:
                    for v in face.verts:
                        if v not in new_verts:
                            new_verts.append(v)

                # Ensure we have exactly 4 unique vertices
                if len(new_verts) == 4:
                    # Calculate the centroid
                    centroid = sum((v.co for v in new_verts), mathutils.Vector()) / 4

                    # Sort vertices by angle relative to the centroid
                    new_verts.sort(key=lambda v: math.atan2(v.co.y - centroid.y, v.co.x - centroid.x))

                    try:
                        # Create the new quad face
                        new_face = bm.faces.new(new_verts)
                        print(f"Created new face: {new_face}")  # Optional debug statement
                    except ValueError:
                        print("Could not create a new face with the vertices:", new_verts)
                        continue  # Skip to the next set of faces

                    # Mark original faces as merged
                    for f in faces_to_merge:
                        merged_faces.add(f)  # Track merged faces
                    
                    # Collect edges to remove
                    edges_to_remove = set()
                    for f in faces_to_merge:
                        edges_to_remove.update(f.edges)
                        
                    # Remove the original faces
                    for f in faces_to_merge:
                        bm.faces.remove(f)
                    
                    # Now remove the edges that are not part of the new face
                    for edge in edges_to_remove:
                        if edge not in new_face.edges:
                            bm.edges.remove(edge)

                    # Ensure lookup table is updated after removing faces
                    bm.faces.ensure_lookup_table()
                    bm.edges.ensure_lookup_table()

        # Update the mesh with the new faces
        bm.to_mesh(mesh)
        bm.free()

        # Switch back to edit mode if necessary
        bpy.ops.object.mode_set(mode='EDIT')



def draw_mesh_context_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(TidyMeshOperator.bl_idname, text=TidyMeshOperator.bl_label)

def register():
    bpy.utils.register_class(TidyMeshOperator)
    
    # Register the context menu
    rcmenu = getattr(bpy.types, "VIEW3D_MT_edit_mesh_context_menu", None)
    if rcmenu is None:
        rcmenu = bpy.types.VIEW3D_MT_edit_mesh_context_menu
        bpy.utils.register_class(rcmenu)

    # Add draw function for the menu
    rcmenu.append(draw_mesh_context_menu)
    print("Registered Tidy Mesh")

def unregister():
    # Unregister the operator and menu
    bpy.utils.unregister_class(TidyMeshOperator)
    rcmenu = bpy.types.VIEW3D_MT_edit_mesh_context_menu
    rcmenu.remove(draw_mesh_context_menu)
    print("Unregistered Tidy Mesh")

# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
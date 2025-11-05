# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "SMPL-X Animation Exporter",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > SMPL-X Exporter",
    "description": "Export SMPL-X animation data to NPZ format",
    "category": "Animation",
}

import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import os
from bpy.props import StringProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup, Operator, Panel
from bpy_extras.io_utils import ExportHelper


# Define joint names
BODY_NAMES = [
    'pelvis', 'left_hip', 'right_hip', 'spine1', 'left_knee', 'right_knee', 'spine2', 
    'left_ankle', 'right_ankle', 'spine3', 'left_foot', 'right_foot', 'neck', 
    'left_collar', 'right_collar', 'head', 'left_shoulder', 'right_shoulder', 
    'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist'
]

HAND_NAMES = [
    'left_index1', 'left_index2', 'left_index3', 'left_middle1', 'left_middle2', 'left_middle3', 
    'left_pinky1', 'left_pinky2', 'left_pinky3', 'left_ring1', 'left_ring2', 'left_ring3', 
    'left_thumb1', 'left_thumb2', 'left_thumb3', 'right_index1', 'right_index2', 'right_index3', 
    'right_middle1', 'right_middle2', 'right_middle3', 'right_pinky1', 'right_pinky2', 'right_pinky3', 
    'right_ring1', 'right_ring2', 'right_ring3', 'right_thumb1', 'right_thumb2', 'right_thumb3'
]

FACE_NAMES = ['jaw', 'left_eye_smplhf', 'right_eye_smplhf']

BONE_NAMES = BODY_NAMES + HAND_NAMES + FACE_NAMES


class SMPLXExporterProperties(PropertyGroup):
    """Properties for SMPL-X Animation Exporter"""
    
    armature_object: PointerProperty(
        name="SMPL-X Armature",
        description="Select the SMPL-X armature object to export",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    
    export_path: StringProperty(
        name="Export Path",
        description="Directory path to save the exported NPZ file",
        default="//",
        subtype='DIR_PATH'
    )
    
    export_filename: StringProperty(
        name="Filename",
        description="Name of the exported NPZ file (without extension)",
        default="smplx_animation"
    )
    
    start_frame: IntProperty(
        name="Start Frame",
        description="First frame to export",
        default=1,
        min=0
    )
    
    end_frame: IntProperty(
        name="End Frame",
        description="Last frame to export",
        default=250,
        min=0
    )
    
    mocap_framerate: IntProperty(
        name="Framerate",
        description="Mocap frame rate (fps)",
        default=60,
        min=1,
        max=240
    )


class SMPLX_OT_ExportAnimation(Operator, ExportHelper):
    """Export SMPL-X animation to NPZ format"""
    bl_idname = "export_anim.smplx_npz"
    bl_label = "Export SMPL-X Animation"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".npz"
    
    filter_glob: StringProperty(
        default="*.npz",
        options={'HIDDEN'}
    )
    
    @classmethod
    def poll(cls, context):
        props = context.scene.smplx_exporter_props
        return props.armature_object is not None
    
    def execute(self, context):
        props = context.scene.smplx_exporter_props
        armature_obj = props.armature_object
        
        if not armature_obj or armature_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select a valid SMPL-X armature object")
            return {'CANCELLED'}
        
        # Validate bone names
        missing_bones = []
        for bone_name in BONE_NAMES:
            if bone_name not in armature_obj.pose.bones:
                missing_bones.append(bone_name)
        
        if missing_bones:
            self.report({'WARNING'}, f"Missing bones: {', '.join(missing_bones[:5])}... Continuing with available bones")
        
        # Get frame range
        start_frame = props.start_frame
        end_frame = props.end_frame
        num_frames = end_frame - start_frame + 1
        
        if num_frames <= 0:
            self.report({'ERROR'}, "Invalid frame range")
            return {'CANCELLED'}
        
        # Initialize arrays
        root_orient = np.zeros((num_frames, 3), dtype=np.float32)
        trans = np.zeros((num_frames, 3), dtype=np.float32)
        poses = np.zeros((num_frames, 162), dtype=np.float32)
        
        scene = context.scene
        
        # Show progress in window manager
        wm = context.window_manager
        wm.progress_begin(0, 100)
        
        try:
            # Extract animation data
            for frame_idx, frame_id in enumerate(range(start_frame, end_frame + 1)):
                # Update progress bar
                progress = int((frame_idx / num_frames) * 100)
                wm.progress_update(progress)
                
                if frame_idx % 50 == 0:
                    print(f"Processing frame {frame_id}/{end_frame} ({frame_idx}/{num_frames}) - {progress}%")
                
                scene.frame_set(frame_id)
                context.view_layer.update()
                
                # Extract root orientation and translation
                if 'pelvis' in armature_obj.pose.bones:
                    pelvis_bone = armature_obj.pose.bones['pelvis']
                    pelvis_global_matrix = armature_obj.matrix_world @ pelvis_bone.matrix
                    
                    # Root orientation (axis-angle)
                    rotation_matrix = pelvis_global_matrix.to_3x3().normalized()
                    rotation_quaternion = rotation_matrix.to_quaternion()
                    axis, angle = rotation_quaternion.to_axis_angle()
                    root_orient[frame_idx] = axis * angle
                    
                    # Translation
                    trans[frame_idx] = pelvis_global_matrix.to_translation()
                
                # Extract joint poses (skip pelvis, start from index 1)
                for bone_name in BONE_NAMES[1:]:
                    if bone_name not in armature_obj.pose.bones:
                        continue
                    
                    pose_bone = armature_obj.pose.bones[bone_name]
                    
                    # Get local rotation
                    if pose_bone.parent:
                        local_matrix = pose_bone.parent.matrix.inverted() @ pose_bone.matrix
                    else:
                        local_matrix = pose_bone.matrix
                    
                    local_rotation_matrix = local_matrix.to_3x3().normalized()
                    local_rotation_quaternion = local_rotation_matrix.to_quaternion()
                    axis, angle = local_rotation_quaternion.to_axis_angle()
                    axis_angle = axis * angle
                    
                    # Store in poses array
                    joint_index = BONE_NAMES.index(bone_name) - 1
                    poses[frame_idx, joint_index*3:joint_index*3+3] = [axis_angle.x, axis_angle.y, axis_angle.z]
            
            # Split poses into body, hand, face
            pose_body = poses[:, :63]
            pose_hand = poses[:, 63:153]
            pose_face = poses[:, 153:]
            
            # Create SMPL-X data dictionary
            betas = np.zeros((16,), dtype=np.float32)
            smplx_data = {
                'gender': 'neutral',
                'surface_model_type': 'smplx',
                'mocap_frame_rate': props.mocap_framerate,
                'betas': betas,
                'root_orient': root_orient,
                'trans': trans,
                'poses': poses,
                'pose_body': pose_body,
                'pose_hand': pose_hand,
                'pose_jaw': pose_face,
                'pose_eye': pose_face,
            }
            
            # Save to NPZ (this might take a moment for large files)
            print("Saving NPZ file...")
            output_path = self.filepath
            np.savez(output_path, **smplx_data)
            
            self.report({'INFO'}, f"Successfully exported animation to {output_path}")
            print(f"Exported SMPL-X animation:")
            print(f"  - Frames: {num_frames}")
            print(f"  - Root orient shape: {root_orient.shape}")
            print(f"  - Translation shape: {trans.shape}")
            print(f"  - Poses shape: {poses.shape}")
            print(f"  - Output: {output_path}")
            
        finally:
            # Always end progress bar
            wm.progress_end()
        
        return {'FINISHED'}


class SMPLX_OT_SetFrameRange(Operator):
    """Set frame range from timeline"""
    bl_idname = "smplx_exporter.set_frame_range"
    bl_label = "Use Timeline Range"
    bl_description = "Set start and end frames from current timeline"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.smplx_exporter_props
        props.start_frame = context.scene.frame_start
        props.end_frame = context.scene.frame_end
        self.report({'INFO'}, f"Frame range set to {props.start_frame}-{props.end_frame}")
        return {'FINISHED'}


class SMPLX_OT_DetectAnimationRange(Operator):
    """Detect full animation range from armature keyframes"""
    bl_idname = "smplx_exporter.detect_animation_range"
    bl_label = "Auto Detect Range"
    bl_description = "Automatically detect the full animation range from all keyframes in the armature"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        props = context.scene.smplx_exporter_props
        return props.armature_object is not None
    
    def execute(self, context):
        props = context.scene.smplx_exporter_props
        armature_obj = props.armature_object
        
        if not armature_obj:
            self.report({'ERROR'}, "No armature selected")
            return {'CANCELLED'}
        
        min_frame = float('inf')
        max_frame = float('-inf')
        keyframe_count = 0
        
        # Check animation data on the armature object itself
        if armature_obj.animation_data and armature_obj.animation_data.action:
            action = armature_obj.animation_data.action
            for fcurve in action.fcurves:
                for keyframe in fcurve.keyframe_points:
                    frame = keyframe.co[0]
                    min_frame = min(min_frame, frame)
                    max_frame = max(max_frame, frame)
                    keyframe_count += 1
        
        # Also check NLA tracks
        if armature_obj.animation_data:
            for track in armature_obj.animation_data.nla_tracks:
                for strip in track.strips:
                    min_frame = min(min_frame, strip.frame_start)
                    max_frame = max(max_frame, strip.frame_end)
                    keyframe_count += 1
        
        # If no keyframes found, try to get from scene
        if keyframe_count == 0 or min_frame == float('inf'):
            self.report({'WARNING'}, "No keyframes found in armature. Using scene frame range.")
            props.start_frame = context.scene.frame_start
            props.end_frame = context.scene.frame_end
            return {'FINISHED'}
        
        # Set the detected range
        props.start_frame = int(min_frame)
        props.end_frame = int(max_frame)
        
        self.report({'INFO'}, f"Detected animation range: {props.start_frame}-{props.end_frame} ({keyframe_count} keyframes)")
        print(f"Animation detection:")
        print(f"  - Start frame: {props.start_frame}")
        print(f"  - End frame: {props.end_frame}")
        print(f"  - Total frames: {props.end_frame - props.start_frame + 1}")
        print(f"  - Keyframes found: {keyframe_count}")
        
        return {'FINISHED'}


class SMPLX_OT_SelectActiveArmature(Operator):
    """Select currently active armature"""
    bl_idname = "smplx_exporter.select_active_armature"
    bl_label = "Use Active Object"
    bl_description = "Use the currently selected armature object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if context.active_object and context.active_object.type == 'ARMATURE':
            props = context.scene.smplx_exporter_props
            props.armature_object = context.active_object
            self.report({'INFO'}, f"Selected armature: {context.active_object.name}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No armature object selected")
            return {'CANCELLED'}


class SMPLX_PT_ExporterPanel(Panel):
    """SMPL-X Animation Exporter Panel"""
    bl_label = "SMPL-X Animation Exporter"
    bl_idname = "SMPLX_PT_exporter_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SMPL-X Export'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.smplx_exporter_props
        
        # Armature selection
        box = layout.box()
        box.label(text="1. Select SMPL-X Armature", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.prop(props, "armature_object", text="")
        row.operator("smplx_exporter.select_active_armature", text="", icon='EYEDROPPER')
        
        if props.armature_object:
            box.label(text=f"Selected: {props.armature_object.name}", icon='CHECKMARK')
        
        layout.separator()
        
        # Frame range
        box = layout.box()
        box.label(text="2. Frame Range", icon='TIME')
        row = box.row(align=True)
        row.prop(props, "start_frame")
        row.prop(props, "end_frame")
        
        # Frame range buttons
        row = box.row(align=True)
        row.operator("smplx_exporter.detect_animation_range", icon='AUTO')
        row.operator("smplx_exporter.set_frame_range", icon='PREVIEW_RANGE')
        
        num_frames = max(0, props.end_frame - props.start_frame + 1)
        box.label(text=f"Total frames: {num_frames}")
        
        # Show animation info if armature is selected
        if props.armature_object and props.armature_object.animation_data:
            if props.armature_object.animation_data.action:
                action = props.armature_object.animation_data.action
                box.label(text=f"Action: {action.name}", icon='ACTION')
        
        layout.separator()
        
        # Settings
        box = layout.box()
        box.label(text="3. Export Settings", icon='SETTINGS')
        box.prop(props, "mocap_framerate")
        
        layout.separator()
        
        # Export button
        box = layout.box()
        box.label(text="4. Export Animation", icon='EXPORT')
        
        if props.armature_object:
            box.operator("export_anim.smplx_npz", text="Export to NPZ", icon='FILE_TICK')
        else:
            box.label(text="Please select an armature first", icon='ERROR')


# Registration
classes = [
    SMPLXExporterProperties,
    SMPLX_OT_ExportAnimation,
    SMPLX_OT_SetFrameRange,
    SMPLX_OT_DetectAnimationRange,
    SMPLX_OT_SelectActiveArmature,
    SMPLX_PT_ExporterPanel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.smplx_exporter_props = PointerProperty(type=SMPLXExporterProperties)
    print("SMPL-X Animation Exporter registered")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.smplx_exporter_props
    print("SMPL-X Animation Exporter unregistered")


if __name__ == "__main__":
    register()

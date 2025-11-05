# SMPL-X Animation Exporter Plugin

A Blender add-on for exporting SMPL-X animation data to NPZ format.

## Features

1. ✅ **GUI for SMPLX Model Selection** - Intuitive interface to select armature objects
2. ✅ **Custom Export Location** - Flexible file path and filename settings
3. ✅ **NPZ Format Export** - Export standard SMPL-X animation data format
4. ✅ **Auto Animation Detection** - Automatically detect full animation range from keyframes

## Installation

1. Open Blender
2. Go to `Edit` → `Preferences` → `Add-ons`
3. Click the `Install...` button
4. Select the `__init__.py` file from the `SMPLX_exporter` folder
5. Enable the add-on by checking `Animation: SMPL-X Animation Exporter`

## Usage

### 1. Open the Plugin Panel
- In the 3D Viewport, press `N` to open the sidebar
- Find the `SMPL-X Export` tab

### 2. Select SMPL-X Armature
- **Method 1**: Choose armature object from the `Select SMPL-X Armature` dropdown menu
- **Method 2**: Select the armature object in the scene, then click the 🔽 (eyedropper icon) button for quick selection

### 3. Set Frame Range
- Manually input `Start Frame` and `End Frame`
- Or click `Auto Detect Range` to automatically detect the full animation range from all keyframes
- Or click `Use Timeline Range` to use the current timeline range

### 4. Configure Export Settings
- `Framerate`: Set animation frame rate (default: 60 fps)

### 5. Export Animation
- Click the `Export to NPZ` button
- Choose save location and filename
- Click `Export SMPL-X Animation` to confirm export

## Export Data Format

The exported NPZ file contains the following data:

```python
{
    'gender': 'neutral',                  # Gender (neutral)
    'surface_model_type': 'smplx',        # Model type
    'mocap_frame_rate': 60,               # Frame rate
    'betas': (16,),                       # Shape parameters
    'root_orient': (N, 3),                # Root bone rotation (axis-angle)
    'trans': (N, 3),                      # Global translation
    'poses': (N, 162),                    # Full pose (body + hand + face)
    'pose_body': (N, 63),                 # Body pose (21 joints × 3)
    'pose_hand': (N, 90),                 # Hand pose (30 joints × 3)
    'pose_jaw': (N, 9),                   # Jaw pose (3 joints × 3)
    'pose_eye': (N, 9),                   # Eye pose (3 joints × 3)
}
```

Where N is the number of frames.

## Armature Requirements

The plugin requires SMPL-X armature to contain the following bones:

### Body Bones (22)
- pelvis, left_hip, right_hip, spine1, left_knee, right_knee, spine2
- left_ankle, right_ankle, spine3, left_foot, right_foot, neck
- left_collar, right_collar, head, left_shoulder, right_shoulder
- left_elbow, right_elbow, left_wrist, right_wrist

### Hand Bones (30)
- left/right: index1-3, middle1-3, pinky1-3, ring1-3, thumb1-3

### Face Bones (3)
- jaw, left_eye_smplhf, right_eye_smplhf

## Troubleshooting

### Issue: Plugin cannot find bones
**Solution**: 
- Ensure your armature object is a standard SMPL-X armature
- Check bone naming is correct
- Plugin will show a warning but continue exporting available bones

### Issue: Exported file is too large
**Solution**: 
- Reduce the exported frame range
- Use a lower frame rate

### Issue: Cannot select armature object
**Solution**: 
- Ensure the selected object type is `ARMATURE`
- Not a Mesh or other object type

### Issue: Animation longer than timeline
**Solution**:
- Click `Auto Detect Range` button to automatically detect the full animation range
- The plugin will scan all keyframes even if they're beyond the timeline range

## Quick Operations

1. **Quick select current object**: Select armature then click the eyedropper icon
2. **Auto detect animation range**: Click `Auto Detect Range` to scan all keyframes
3. **Use timeline range**: Click `Use Timeline Range` to use current timeline settings
4. **Batch export**: Repeatedly use the plugin to export different animation segments

## Technical Details

- Rotation representation: Axis-Angle format
- Coordinate system: Blender global coordinate system
- Units: Meters (m)
- Data type: float32

## Version Information

- **Version**: 1.0.0
- **Compatibility**: Blender 3.6.0+
- **License**: GPL v2

## Credits

Based on the original `blender_smplx.py` script, improved with reference to the SMPL-X Blender add-on implementation logic.

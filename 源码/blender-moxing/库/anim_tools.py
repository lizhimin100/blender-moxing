"""anim_tools.py —— 在 Blender 5.2 的 layered action 上改关键帧。

动作是从原 GLB 导入的（每帧都有键、370 条曲线），这里只做三类外科手术：
  lock_bones()   把某几根骨的旋转/位移锁到 rest（修"手绕弩转"）
  scale_rot()    把某几根骨的旋转角整体放大/缩小（修攻击幅度）
  add_local_rot() 给某根骨叠加一个固定旋转（修头/武器的基准姿态）
"""
import math

from mathutils import Quaternion, Vector


def fcurves(act):
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def _by_path(act):
    d = {}
    for fc in fcurves(act):
        d.setdefault(fc.data_path, {})[fc.array_index] = fc
    return d


def lock_bones(act, bones, loc=True):
    """把这些骨的 rotation_quaternion 写回 (1,0,0,0)，location 写回 0。"""
    d = _by_path(act)
    n = 0
    for b in bones:
        rp = 'pose.bones["%s"].rotation_quaternion' % b
        if rp in d:
            ch = d[rp]
            for i in range(4):
                if i in ch:
                    for kp in ch[i].keyframe_points:
                        kp.co[1] = 1.0 if i == 0 else 0.0
                        kp.handle_left[1] = kp.co[1]
                        kp.handle_right[1] = kp.co[1]
            n += 1
        if loc:
            lp = 'pose.bones["%s"].location' % b
            if lp in d:
                for i, fc in d[lp].items():
                    for kp in fc.keyframe_points:
                        kp.co[1] = 0.0
                        kp.handle_left[1] = 0.0
                        kp.handle_right[1] = 0.0
    for fc in fcurves(act):
        fc.update()
    return n


def scale_rot(act, bones, factor):
    """按四元数轴角放大旋转（factor>1 更夸张）。逐帧读取四分量再写回。"""
    d = _by_path(act)
    for b in bones:
        rp = 'pose.bones["%s"].rotation_quaternion' % b
        if rp not in d:
            continue
        ch = d[rp]
        if not all(i in ch for i in range(4)):
            continue
        n = len(ch[0].keyframe_points)
        for k in range(n):
            q = Quaternion([ch[i].keyframe_points[k].co[1] for i in range(4)])
            if q.magnitude < 1e-8:
                continue
            q.normalize()
            ang = q.angle
            if abs(ang) < 1e-6:
                continue
            axis = q.axis
            q2 = Quaternion(axis, min(ang * factor, math.pi * 0.98))
            vals = (q2.w, q2.x, q2.y, q2.z)
            for i in range(4):
                kp = ch[i].keyframe_points[k]
                kp.co[1] = vals[i]
                kp.handle_left[1] = vals[i]
                kp.handle_right[1] = vals[i]
    for fc in fcurves(act):
        fc.update()


def add_local_rot(act, bone, axis, angle_deg):
    """在骨局部空间叠加一个固定旋转（乘在现有旋转的右边）。"""
    d = _by_path(act)
    rp = 'pose.bones["%s"].rotation_quaternion' % bone
    if rp not in d:
        return False
    ch = d[rp]
    add = Quaternion(Vector(axis).normalized(), math.radians(angle_deg))
    n = len(ch[0].keyframe_points)
    for k in range(n):
        q = Quaternion([ch[i].keyframe_points[k].co[1] for i in range(4)])
        q.normalize()
        q2 = q @ add
        vals = (q2.w, q2.x, q2.y, q2.z)
        for i in range(4):
            kp = ch[i].keyframe_points[k]
            kp.co[1] = vals[i]
            kp.handle_left[1] = vals[i]
            kp.handle_right[1] = vals[i]
    for fc in fcurves(act):
        fc.update()
    return True


def action_names():
    import bpy
    return [a.name for a in bpy.data.actions]


def get(name):
    import bpy
    return bpy.data.actions.get(name)


def remove_bone_curves(act, bone, prop="rotation_quaternion"):
    """删掉某根骨某属性的全部 fcurve（layered action 也一样）。"""
    path = 'pose.bones["%s"].%s' % (bone, prop)
    n = 0
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in list(bag.fcurves):
                    if fc.data_path == path:
                        bag.fcurves.remove(fc)
                        n += 1
    return n


def set_quat_keys(act, arm, bone, frames_angles, axis=(0, 0, 1), scene=None):
    """按 (frame, angle_deg) 写一组局部四元数关键帧；先删旧曲线。"""
    import bpy
    import math
    from mathutils import Quaternion
    scene = scene or bpy.context.scene
    remove_bone_curves(act, bone, "rotation_quaternion")
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    pb = arm.pose.bones[bone]
    for f, ang in frames_angles:
        scene.frame_set(f)
        pb.rotation_quaternion = Quaternion(axis, math.radians(ang))
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
    for fc in fcurves(act):
        if fc.data_path == 'pose.bones["%s"].rotation_quaternion' % bone:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
    return len(frames_angles)

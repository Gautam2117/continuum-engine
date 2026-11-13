"""Original Low Battery 3D blocking. Positions are in room coordinates."""

from mathutils import Vector


def scenes(bm):
    def pip_room(_params, frames, _palette):
        ink = bm.mat("Pip porcelain", "#fae6c7")
        dark = bm.mat("Pip face", "#2b2433")
        amber = bm.mat("Pip scarf", "#f9aa57")
        couch = bm.mat("Couch upholstery", "#716486")
        wood = bm.mat("Table wood", "#a76951")
        floor = bm.mat("Floor", "#464055")
        screen = bm.mat("Phone display", "#83e4df")

        bm.box("Floor", (12, 12, .12), (0, 0, -.06), floor)
        bm.box("Wall", (12, .15, 7), (0, 2.4, 3.5), floor)
        bm.box("Couch back", (2, .26, 1.04), (-.65, .7, .86), couch)
        bm.box("Couch seat", (2, 1.05, .43), (-.65, .17, .45), couch)
        bm.box("Couch arm", (.25, 1.1, .61), (-1.56, .15, .66), couch)
        bm.box("Side table", (.85, .68, .1), (1.02, -.07, .77), wood)
        for x in (.69, 1.35):
            bm.box("Table support", (.09, .44, .74), (x, -.07, .37), wood)
        bm.cyl("Lamp stem", .037, .81, (1.23, .12, 1.21), wood)
        bm.cyl("Lamp shade", .23, .33, (1.23, .12, 1.69), amber, verts=24)

        phone = bm.box("Phone", (.24, .13, .04), (.77, -.27, .845), dark)
        display = bm.box("Phone display", (.20, .10, .008), (.77, -.27, .87), screen)
        head = bm.cyl("Pip head", .26, .25, (-.63, -.18, 1.67), ink, verts=32, rot=(1.5708, 0, 0))
        hand_tip = bm.cyl("Pip hand", .041, .095, (0, 0, 0), ink, verts=16, rot=(0, 1.5708, 0))
        eye = bm.box("Pip eye", (.044, .032, .053), (-.54, -.31, 1.71), dark)
        scarf = bm.box("Pip scarf", (.31, .23, .09), (-.62, -.17, 1.36), amber)
        torso = bm.cyl("Pip torso", .05, 1, (0, 0, 0), ink, verts=16)
        upper = bm.cyl("Pip reaching upper arm", .039, 1, (0, 0, 0), ink, verts=16)
        fore = bm.cyl("Pip reaching forearm", .034, 1, (0, 0, 0), ink, verts=16)
        other_upper = bm.cyl("Pip resting upper arm", .035, 1, (0, 0, 0), ink, verts=16)
        other_fore = bm.cyl("Pip resting forearm", .031, 1, (0, 0, 0), ink, verts=16)
        legs = [bm.cyl(name, .045, 1, (0, 0, 0), ink, verts=16)
                for name in ("Far thigh", "Far shin", "Near thigh", "Near shin")]

        def limb(obj, start, end, frame):
            delta = Vector(end) - Vector(start)
            obj.location = (Vector(start) + Vector(end)) / 2
            obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
            obj.scale.z = delta.length
            for field in ("location", "rotation_euler", "scale"):
                obj.keyframe_insert(field, frame=frame)

        camera, target = bm.camera((3.0, -7, 3.3), (-.12, 0, 1.16), lens=40)
        # Anticipation, reach, sustained contact, slip, recoil, deadpan.
        for t, lean, hand, phone_x in (
            (0, 0, -.26, .77), (.18, -.13, -.36, .77), (.44, .49, .65, .77),
            (.57, .54, .78, .89), (.70, -.20, -.28, 1.19), (1, 0, -.26, 1.19),
        ):
            frame = 1 + t * (frames - 1)
            shoulder = (-.64 + lean, -.18, 1.33 - max(0, lean) * .38)
            limb(torso, (-.71, -.16, .72), shoulder, frame)
            limb(upper, shoulder, (-.42 + lean, -.31, 1.0), frame)
            limb(fore, (-.42 + lean, -.31, 1.0), (hand, -.31, .87), frame)
            limb(other_upper, shoulder, (-.84 + lean * .4, -.07, 1.02), frame)
            limb(other_fore, (-.84 + lean * .4, -.07, 1.02), (-.68, -.22, .76), frame)
            for leg in range(2):
                y = -.17 - leg * .18
                knee = (-.28 + lean * .13, y - .22, .65 + (leg * .12 if t == .70 else 0))
                limb(legs[2 * leg], (-.71, y, .72), knee, frame)
                limb(legs[2 * leg + 1], knee, (-.19, y - .32, .10), frame)
            for obj, loc in ((head, (shoulder[0], -.18, shoulder[2] + .32)),
                             (eye, (shoulder[0] + .09, -.32, shoulder[2] + .36)),
                             (scarf, (shoulder[0], -.17, shoulder[2] + .025)),
                             (hand_tip, (hand, -.31, .87)),
                             (phone, (phone_x, -.27, .845)), (display, (phone_x, -.27, .87)),
                             (target, (-.13 + .10 * t, 0, 1.02))):
                obj.location = loc
                obj.keyframe_insert("location", frame=frame)
            camera.data.lens = 40 + t * 4
            camera.data.keyframe_insert("lens", frame=frame)

    return {"pip_room": pip_room}

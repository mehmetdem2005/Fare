# Right knee follow-up

Blender 5.1.2 evaluated frames 1–24 of the swing-clearance action on the ankle Basis trial and each variant. Frame 25 was sampled as the loop closure and excluded from cycle counts.

| Variant | Body intersection events | Events on frames 7 / 8 / 9 | Ventral events |
| --- | ---: | ---: | ---: |
| Ankle Basis trial | 80 | 12 / 10 / 7 | 0 |
| Local thigh/shin weight smoothing | 126 | 20 / 16 / 16 | 0 |
| Blender Preserve Volume | 100 | 12 / 13 / 7 | 0 |
| Local thigh/shin contrast increase | 75 | 9 / 9 / 6 | 0 |

The weight trials use five edge rings around the known frame 7 witness. They change the split between thigh and shin while keeping the combined influence per vertex fixed. The unposed control render has an existing indentation at the leg attachment. The posed close-ups on frames 7 and 8 have a much sharper crease. Increasing the weight contrast reduces some intersections, but the crease is still conspicuous in the matched renders. Neither weight trial nor the volume toggle qualifies as a repair. The shoulder and the perceived torso softness remain open.

## Connectivity and rest geometry

In the two frame 7 witness triangles, every edge incident to the six vertex IDs (10364, 10312, 10533, 10927, 10501, 10258) has exactly two incident faces. This rules out a local open or over-shared edge at the witnesses. It does not rate the quality of the edge layout.

Changing only the rest coordinates in a tapered five-ring patch, with the same displacements applied to all morph blocks, reduces body events from 80 to 60 and leaves the measured ventral patch at zero. Frames 7–9 change from 12 / 10 / 7 to 4 / 4 / 1. Combining the rest edit with the earlier weight contrast increase also gives 60 events. Matched renders still show the crease. Muting all existing morphs leaves the crease visible at frame 7 and gives 76 body events and one ventral event.

The rest geometry contributes to the defect even when connectivity and bone motion are held fixed. The unposed witness pair does not intersect, and isolated thigh and shin transform changes can eliminate the intersection at frame 7. These are separate observations about the rest surface and the pose. They do not establish that the raw edge layout needs replacement.

A local post-armature Corrective Smooth on the Basis trial softened some fine wrinkles, left the major fold visible, and kept the cycle at 60 body events and zero measured ventral events. It was rejected at visual review.

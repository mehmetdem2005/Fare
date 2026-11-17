#!/usr/bin/env bash
# Run from the Fare checkout. Pass the Blender binary and a fresh output path.
set -euo pipefail
blender=$1
root=$2
mkdir "$root"
blender=$(realpath "$blender")
source=deliver/mouse_rig.blend
source_hash=173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6
check_source() { printf '%s  %s\n' "$source_hash" "$source" | sha256sum -c; }
check_source
trap check_source EXIT
git rev-parse HEAD > "$root/commit.txt"
"$blender" --version > "$root/blender-version.txt"
run() {
    local script=$1
    shift
    printf '%q ' "$blender" -b -t 4 --python-exit-code 1 -P "rig-experiments/$script.py" -- "$@" >> "$root/commands.log"
    printf '\n' >> "$root/commands.log"
    "$blender" -b -t 4 --python-exit-code 1 -P "rig-experiments/$script.py" -- "$@"
}

if [[ $# -ge 3 ]]; then
    v8=$3
else
    mkdir -p "$root"/{Base,Weight,Optimization,Verified,Round13}
    run animate_run_v4 --source "$source" --out "$root/Base"
    run v4_flank_weight_trials --source "$root/Base/mouse_run_sprint_v4.blend" --out "$root/Weight"
    run optimize_spine_phase --source "$root/Weight/mouse_sprint_v4_flank_65_EXPERIMENT.blend" --out "$root/Optimization"
    run verify_phase_and_ik --source "$root/Optimization/mouse_run_v6_spine_phase_REVIEW.blend" \
        --optimizer "$root/Optimization/spine_phase_optimization.json" --out "$root/Verified"
    run round13_combined_ik --source "$root/Verified/fare_run_v7_verified_candidate.blend" --out "$root/Round13"
    v8="$root/Round13/run_sprint_v8_ik_phase_NUMERIC_REVIEW.blend"
fi
sha256sum "$v8" > "$root/v8.sha256"
run anatomy_torso_weight_trial --source "$v8" --out "$root/wide" --strength 1.0 --wide-transition
run anatomy_shoulder_motion_trial --source "$root/wide/TORSO_WEIGHT_TRIAL_UNAPPROVED.blend" --out "$root/shoulder"
run anatomy_swing_clearance_trial --source "$root/shoulder/SCAPULAR_MOTION_TRIAL_UNAPPROVED.blend" \
    --out "$root/down12" --direction down --drop .012
run anatomy_ankle_basis_trial --source "$root/down12/SWING_CLEARANCE_TRIAL_UNAPPROVED.blend" --out "$root/ankle"
run anatomy_knee_trial --source "$root/ankle/ANKLE_BASIS_TRIAL_UNAPPROVED.blend" --out "$root/knee.blend" --mode basis
run anatomy_expression_rig "$root/knee.blend" "$root/expressions.blend"
run anatomy_spine_rig "$root/expressions.blend" "$root/spine"

action=run_sprint_v8_swing_clearance_TRIAL
parent="$root/spine/SPINE_RIG_EXPERIMENT.blend"
run anatomy_pose_corrective_trial "$parent" "$action" "$root/knee-taubin" --rings 10 --steps 30 --taubin
run anatomy_expression_export "$root/knee-taubin/KNEE_POSE_CORRECTIVE_UNAPPROVED.blend" "$action" "$root/export"
blend="$root/export/FARE_POSE_REVIEW_UNAPPROVED.blend"
glb="$root/export/FARE_POSE_REVIEW_UNAPPROVED.glb"
run anatomy_manual_replay "$parent" "$action" "$root/current-annotate"
run anatomy_manual_replay "$blend" "$action" "$root/taubin-delivery-annotate"
run anatomy_mesh_roundtrip "$blend" "$glb" "$action" "$root/export/mesh_roundtrip.json"
run anatomy_pose_acceptance "$blend" "$root/export/reopened_pose"
run anatomy_baseline --source "$blend" --action "$action" --expected-bones 52 \
    --full-body-intersections --stage-probes --render --out "$root/taubin-delivery-sprint"
sha256sum "$parent" "$blend" "$glb" > "$root/artifacts.sha256"

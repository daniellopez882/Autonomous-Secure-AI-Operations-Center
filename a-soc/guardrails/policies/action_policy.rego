# A-SOC action policy.
#
# This is the deployable policy for an external OPA sidecar. It must return the
# same verdicts as guardrails/decision.py, which is the in-process authority.
# tests/unit/test_guardrail_policy.py asserts parity across POLICY_PARITY_CASES;
# editing one side without the other fails the build.
#
# The previous version disagreed with the Python scorer in two ways:
#
#   * `require_approval` fired only for 0.5 <= score < 0.8, so a 0.9-risk
#     destructive action matched no approval rule at all, while `allow`
#     required approval.granted -- leaving it in a state that was neither
#     approvable nor deniable.
#   * `allow_iam_revoke` and `allow_pod_isolation` were defined but never
#     referenced by `allow`, so they had no effect on any decision.
#
# Decision precedence, matching decision.py exactly:
#   1. deny            -- destructive and score >= 0.95, without emergency override
#   2. require_approval -- score >= 0.5, or the action is destructive
#   3. allow           -- everything else

package asoc.actions

import future.keywords.if
import future.keywords.in

# Thresholds, kept in one place so they are greppable against decision.py.
approval_threshold := 0.5
deny_threshold := 0.95

destructive_actions := {"K8S_TERMINATE", "K8S_ISOLATE", "IAM_REVOKE"}

# Older scenario names resolved to canonical ones, mirroring ACTION_ALIASES.
action_aliases := {
	"ISOLATE_INSTANCE": "K8S_ISOLATE",
	"BLOCK_IP": "NETWORK_BLOCK",
	"TERMINATE_INSTANCE": "K8S_TERMINATE",
	"REVOKE_CREDENTIALS": "IAM_REVOKE",
}

canonical_action := action_aliases[input.action.type]

canonical_action := input.action.type if {
	not action_aliases[input.action.type]
}

is_destructive if canonical_action in destructive_actions

default decision := "allow"

decision := "deny" if {
	input.action.risk_score >= deny_threshold
	is_destructive
	not input.emergency_override
}

decision := "require_approval" if {
	not deny_condition
	input.action.risk_score >= approval_threshold
}

decision := "require_approval" if {
	not deny_condition
	is_destructive
}

deny_condition if {
	input.action.risk_score >= deny_threshold
	is_destructive
	not input.emergency_override
}

# Convenience rules for callers that want booleans rather than the string.
default allow := false

allow if decision == "allow"

allow if {
	decision == "require_approval"
	input.approval.granted == true
	input.approval.approver != ""
}

default require_approval := false

require_approval if decision == "require_approval"

default deny := false

deny if decision == "deny"

# Every action that is not trivially safe is audited.
default audit_required := false

audit_required if decision != "allow"

audit_required if is_destructive

package asoc.actions

# Default deny all actions
default allow = false
default require_approval = false

# Allow low-risk, non-destructive actions
allow {
    input.action.risk_score < 0.5
    input.action.type != "destructive"
}

# Require approval for medium-risk actions
require_approval {
    input.action.risk_score >= 0.5
    input.action.risk_score < 0.8
}

# Require approval for all destructive actions
require_approval {
    input.action.type == "destructive"
}

# Block extremely high-risk actions entirely
deny {
    input.action.risk_score >= 0.95
    input.action.type == "destructive"
    not input.emergency_override
}

# Allow with approval for high-risk actions
allow {
    input.action.risk_score >= 0.5
    input.approval.granted == true
    input.approval.approver != ""
}

# Specific action policies
allow_iam_revoke {
    input.action.type == "IAM_REVOKE"
    input.action.risk_score >= 0.7
    input.approval.granted == true
}

allow_pod_isolation {
    input.action.type == "K8S_ISOLATE"
    input.action.risk_score >= 0.6
    input.approval.granted == true
}

# Audit requirements
audit_required {
    input.action.type == "destructive"
}

audit_required {
    input.action.risk_score >= 0.5
}

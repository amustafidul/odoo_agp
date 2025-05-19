# Dynamic Approval Workflow Engine for Odoo 16

## Overview

The `ami_approval_workflow_engine` module provides a flexible and dynamic approval system that can be applied to various models in Odoo. This module allows administrators to define multi-level approval flows based on roles, users, or direct supervisors, and sync them to specific target models.

## Key Features

- Dynamic approval workflow creation per model
- Supports approval by:
  - Specific users
  - Job positions (jabatan)
  - Role groups
  - Direct supervisors
- Sync approval flow to specific models (excluding sensitive models)
- Approval type control: Nominal-based or Non-nominal
- Support for chatter and mail activity tracking
- Integrated with `hr.leave` and other custom models
- Admin override and superuser support
- Lightweight custom styling for a clean UI

## Installation

1. Copy this module to your Odoo `addons` directory.
2. Ensure dependencies (`mail`, `hr`, `agp_employee_ib`) are installed.
3. Update the app list and install the module via Apps.

```bash
$ ./odoo-bin -u ami_approval_workflow_engine -d your_db_name
```

## Dependencies

- `base`
- `mail`
- `hr`
- `agp_employee_ib` (custom module dependency)

## Security Groups

| Group Name           | Description                                  |
|----------------------|----------------------------------------------|
| Approval Admin       | Full access to create and manage workflows   |
| Approval Viewer      | Read-only access to view workflows           |

## Access Control

| Model                     | Group               | Read | Write | Create | Delete |
|--------------------------|---------------------|------|-------|--------|--------|
| `approval.workflow`      | Approval Admin      | ✅   | ✅    | ✅     | ✅     |
|                          | Approval Viewer     | ✅   | ❌    | ❌     | ❌     |
| `approval.workflow.line` | Approval Admin      | ✅   | ✅    | ✅     | ✅     |
|                          | Approval Viewer     | ✅   | ❌    | ❌     | ❌     |

## Notes

- Certain core models are **blacklisted** and cannot be used for workflow syncing for security and integrity reasons (e.g., `res.users`, `account.move`, etc.).
- Cron logic should be configured to run only on eligible workflows (to be refined with logging and filters).
- All models using this approval should implement a `state` field that reflects the approval stage.

## Screenshots

_You can place UI screenshots here showing the workflow config and synced result._

## License

LGPL-3

## Author & Maintainer

Ahmad Mustafidul Ibad  
📧 `amustafidul@gmail.com`

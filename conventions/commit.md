# Types of commit

| Type                                                                                                                  | message prefix |
| --------------------------------------------------------------------------------------------------------------------- | -------------- |
| feature                                                                                                               | `feat`         |
| change in behavior, that impacts the user                                                                             | `upd`          |
| bug fixes, that positively impacts the user                                                                           | `fix`          |
| operational capability                                                                                                | `ops:`         |
| product health improvements, e.g. documentations, maintenance                                                         | `chore:`       |
| broken down commits as part of a bigger new change <br> to help with improving understanding and safety <br>of change | `wip:`         |
| verification of acceptance criteria                                                                                   | `ac:`          |
| code organisation or refactor, typically to create new/shared abstractions to be used by existing and new feature     | `rftr:`        |

# Focus area

Commits should reflect best effort be single focus area.

# Message

Commit message should reflect best effort to indicate outcome instead of the work.

If there are any non-obvious reason/details for the change, add a short note on the second line of the commit message.

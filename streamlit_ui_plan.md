# Streamlit UI Implementation Plan

## App Goal

Build a student-facing Streamlit enrollment app for the existing student enrollment backend in `enrollment_starter.py`.

The student is assumed to already be authenticated before opening the app. For this phase, the UI will use the existing simulated student object:

- `CURRENT_STUDENT["user_id"]`
- `CURRENT_STUDENT["name"]`
- `CURRENT_STUDENT["email"]`

The app should let the current student:

- View actively enrolled classes.
- Enter an enrollment key.
- Enroll in a new class.
- Re-enroll in a previously unenrolled class.
- Open a selected class page.
- Soft-unenroll from an active class.

This document is a planning document only. It does not require writing Streamlit code yet.

## Assumptions

## Do

- Use the existing seeded or simulated student from the backend.
- Treat `CURRENT_STUDENT` as the already-authenticated user for this phase.
- Check that the current user role is `Student` before showing the student-facing UI.
- Use `st.session_state` to store and track role, page, selected class, and short feedback messages.
- Preserve the existing layered backend design:
  - `Database` handles SQLite persistence.
  - `EnrollmentService` handles enrollment business actions.
  - Streamlit UI handles presentation, routing, and user interaction.
- Have the Streamlit UI call service-layer methods for enrollment actions.
- Keep database and service-layer changes minimal unless the UI cannot cleanly perform a required action through the service layer.

## Do Not

- Do not build login.
- Do not build registration.
- Do not build password handling.
- Do not build account creation.
- Do not create a new authentication system.
- Do not directly modify enrollment rows from the Streamlit UI.
- Do not delete enrollment rows when a student unenrolls.

## Backend Integration

The UI should import and reuse the backend objects from `enrollment_starter.py`:

- `CURRENT_STUDENT`
- `DB_PATH`
- `STATUS_ENROLLED`
- `STATUS_UNENROLLED`
- `Database`
- `EnrollmentService`

Recommended startup flow:

1. Create a `Database(DB_PATH)` instance.
2. Call `database.create_tables()`.
3. Call `database.seed_sample_data()`.
4. Create `EnrollmentService(database)`.
5. Read the current student from `CURRENT_STUDENT`.

The Streamlit UI should use the service layer as the main way to get enrollment data and perform enrollment actions. The UI should avoid calling database methods directly unless there is no service method available yet.

The UI should call existing service methods for student actions:

- `service.enroll_with_key(user_id, email, enrollment_key)`
- `service.soft_unenroll_student(user_id, course_id)`
- `service.get_student_summary(user_id)`

The current backend has student enrollment read methods on `Database`, such as:

- `database.get_student_enrollments(user_id)`
- `database.get_student_enrollment_history(user_id)`
- `database.get_student_course_record(user_id, course_id)`

For this phase, prefer adding simple service-layer pass-through methods when read access is needed by the UI. For example, add `service.get_student_enrollments(user_id)` as a small wrapper around `database.get_student_enrollments(user_id)` so the UI stays clean and does not need to know database details.

If implementation time is limited, the UI may call a database read method only when there is no service method available yet. Any direct database read from the UI should be treated as temporary and should not directly update database rows.

## Session State Design

Initialize these keys near the top of the Streamlit app before rendering pages:

| Session key | Purpose | Default value |
| --- | --- | --- |
| `st.session_state["role"]` | Stores the current user role. | `"Student"` |
| `st.session_state["page"]` | Controls which page renders. | `"dashboard"` |
| `st.session_state["selected_class"]` | Stores the selected class record or `None`. | `None` |
| `st.session_state["feedback_message"]` | Stores a short message after an action. | `""` |
| `st.session_state["feedback_type"]` | Stores how feedback should display. | `""` |

Valid page values:

- `"dashboard"`
- `"class_detail"`

Valid feedback type values:

- `"success"` for `st.success`
- `"warning"` for `st.warning`
- `"error"` for `st.error`
- `""` when there is no message to display

The feedback message should be short and action-specific, such as:

- `Enrolled in Web Apps With Streamlit.`
- `Enrollment key not found. Please check the key and try again.`
- `You have unenrolled from Data Storytelling.`

## Role Check

Before rendering the student dashboard or selected class page, check:

- `st.session_state["role"] == "Student"`

If the role is missing or not `Student`:

1. Store or display an error message.
2. Use `st.error`.
3. Stop rendering the student UI.

No login or role-selection UI should be built in this phase. The role can be initialized as `"Student"` because the student is assumed to be authenticated already.

## Routing Design

Use `st.session_state["page"]` as the simple router.

At render time:

1. If `page == "dashboard"`, render the student dashboard.
2. If `page == "class_detail"`, render the selected class page.
3. If `page` has an unexpected value, reset it to `"dashboard"`.

When a student clicks `Go to Class`:

1. Store that class dictionary in `st.session_state["selected_class"]`.
2. Set `st.session_state["page"] = "class_detail"`.
3. Refresh with `st.rerun()`.

When a student successfully enrolls or re-enrolls with a key:

1. Use the returned enrollment record to identify the course.
2. Store the selected class details in `st.session_state["selected_class"]`.
3. Set `st.session_state["page"] = "class_detail"`.
4. Store a success feedback message.
5. Refresh with `st.rerun()`.

When a student clicks `Back to Dashboard`:

1. Set `st.session_state["page"] = "dashboard"`.
2. Either clear `st.session_state["selected_class"]` or preserve it for convenience.
3. Refresh with `st.rerun()`.

Recommended behavior: clear `selected_class` when returning to the dashboard so page state stays simple.

## Dashboard Layout

The dashboard should start with:

- `st.title("Student Dashboard")`
- `st.caption("View your enrolled classes or use an enrollment key to join a class.")`

Use `st.container` and `st.columns` to organize the page into readable sections:

- Current student summary.
- Active enrolled classes.
- Enrollment key form.

Possible layout:

- Top container:
  - Student name and email.
  - Summary metrics from `service.get_student_summary(user_id)`.
- Main area:
  - Left or full-width section for active classes.
  - Right or lower section for enrollment key entry.

## Enrolled Classes Section

Retrieve active enrollments for the current student through the service layer:

- Prefer adding and using `service.get_student_enrollments(user_id)`.
- Use `database.get_student_enrollments(user_id)` only as a temporary fallback if the service wrapper has not been added yet.

Display the enrolled classes with either:

- `st.dataframe` for a compact table, or
- A clean list using `st.container` and `st.columns` for each class.

Recommended class row fields:

- Course code: `course_id`
- Course name: `course_name`
- Instructor: `instructor`
- Status: `status`
- Enrolled date: `enrolled_at`

For each active class, include:

- `Go to Class` button.
- `Unenroll` button.

Button keys should include the course ID, such as:

- `go_to_class_MISY350`
- `unenroll_MISY350`

If no active classes are found:

- Use `st.warning("You are not currently enrolled in any classes.")`
- Keep the enrollment key form visible.

## Enrollment Key Section

Use a Streamlit form:

- `st.form`
- `st.text_input`
- `st.form_submit_button`

The form should ask for an enrollment key and submit it as one action.

Submission flow:

1. Read and trim the enrollment key from the form.
2. Call `service.enroll_with_key(CURRENT_STUDENT["user_id"], CURRENT_STUDENT["email"], enrollment_key)`.
3. If the service returns a record, treat it as a successful enroll or re-enroll.
4. If the service returns `None`, treat it as an invalid key or invalid input.

Success behavior:

- Store `st.session_state["feedback_type"] = "success"`.
- Store a clear success message.
- Store the selected class in `st.session_state["selected_class"]`.
- Set `st.session_state["page"] = "class_detail"`.
- Refresh the UI.

Invalid key behavior:

- Store `st.session_state["feedback_type"] = "error"`.
- Store a clear error message.
- Keep `st.session_state["page"] = "dashboard"`.
- Do not change `selected_class`.

## Selected Class Page Layout

The selected class page should render after:

- A successful enrollment or re-enrollment.
- A student clicks `Go to Class`.

If `st.session_state["selected_class"]` is missing:

1. Store a warning message.
2. Set `st.session_state["page"] = "dashboard"`.
3. Refresh or render the dashboard.

The page should use:

- `st.title`
- `st.caption`
- `st.container`
- `st.columns`
- `st.metric`
- `st.divider`
- `st.expander` if extra details are useful

Recommended content:

- Title: course name or course code.
- Caption: instructor and enrollment status.
- Metrics:
  - Course code.
  - Enrollment status.
  - Enrolled date if available.
- Detail section:
  - Course name.
  - Instructor.
  - Student name.
  - Student email.

Include a `Back to Dashboard` button:

1. Set `st.session_state["page"] = "dashboard"`.
2. Clear `st.session_state["selected_class"]`.
3. Refresh with `st.rerun()`.

Optional: include an `Unenroll` button on the selected class page too. If included, it should call the same service-layer soft-unenroll method and return the student to the dashboard afterward.

## Actions and Feedback

Feedback should be stored in session state so it survives a page change or refresh.

Create a small rendering pattern near the top of each page:

- If `feedback_message` exists and `feedback_type == "success"`, call `st.success`.
- If `feedback_type == "warning"`, call `st.warning`.
- If `feedback_type == "error"`, call `st.error`.

Recommended message behavior:

- Feedback messages should show only once after an action.
- After displaying `st.success`, `st.warning`, or `st.error`, clear `st.session_state["feedback_message"]` and `st.session_state["feedback_type"]`.
- This prevents old messages from staying on the screen after later reruns.

Use feedback types consistently:

- `st.success`: successful enrollment or re-enrollment.
- `st.error`: invalid enrollment key or non-student role.
- `st.warning`: soft-unenrollment or no active classes found.

## Enrollment Flow

1. Student enters an enrollment key.
2. UI calls `EnrollmentService.enroll_with_key`.
3. Service validates the key using the backend.
4. If valid, service enrolls or reactivates the student.
5. UI stores a success message.
6. UI stores the selected class.
7. UI routes to the selected class page.

Implementation note: `Database.enroll_student` already uses an upsert to set `status = "enrolled"` and update `enrolled_at`, so the same flow can support both new enrollment and re-enrollment.

## Invalid Key Flow

1. Student enters an invalid enrollment key.
2. UI calls `EnrollmentService.enroll_with_key`.
3. Service returns `None`.
4. UI stores `feedback_type = "error"`.
5. UI stores a clear error message.
6. Student remains on the dashboard.

Recommended error text:

`Enrollment key not found. Please check the key and try again.`

## Soft-Unenroll Flow

1. Student clicks `Unenroll` for an active class.
2. UI calls `EnrollmentService.soft_unenroll_student(user_id, course_id)`.
3. Service calls the database layer.
4. Database updates the existing enrollment record to `status = "unenrolled"`.
5. The row remains in the database.
6. UI stores a short feedback message in `st.session_state`.
7. UI refreshes or returns the user to the dashboard.
8. Dashboard reloads active enrollments.
9. The unenrolled class no longer appears as actively enrolled.

Recommended warning text:

`You have unenrolled from COURSE_NAME.`

If the service returns `False`, show an error message instead:

`Could not unenroll from this class. Please try again.`

## Minimal Backend Changes To Consider Later

The current backend is already close to what the UI needs. To keep the Streamlit UI clean, prefer adding small service-layer pass-through methods before calling database methods directly from the UI:

- `get_student_enrollments(user_id)`
- `get_student_enrollment_history(user_id)`
- `get_student_course_record(user_id, course_id)`

These should delegate to existing `Database` methods and should not duplicate SQL in the UI.

Avoid changing table structure, authentication, seeded data, or enrollment rules unless a later requirement makes that necessary.

## Implementation Order

1. Create a Streamlit entry file only after this plan is approved.
2. Import backend constants and classes from `enrollment_starter.py`.
3. Initialize database, seed data, service, and session state.
4. Add the student role guard.
5. Build the dashboard route.
6. Add active enrollment display.
7. Add `Go to Class` routing.
8. Add enrollment key form.
9. Add selected class page route.
10. Add soft-unenroll buttons.
11. Add feedback rendering.
12. Manually test:
    - Existing active enrollment appears.
    - Valid key enrolls or re-enrolls.
    - Invalid key stays on dashboard with an error.
    - `Go to Class` opens the selected class page.
    - `Back to Dashboard` returns to dashboard.
    - Unenroll changes status without deleting the row.

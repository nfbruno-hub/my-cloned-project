from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from enrollment_starter import (
    CURRENT_STUDENT,
    DB_PATH,
    STATUS_ENROLLED,
    STATUS_UNENROLLED,
    Database,
    EnrollmentService,
)


DASHBOARD_PAGE = "dashboard"
CLASS_DETAIL_PAGE = "class_detail"
STUDENT_ROLE = "Student"


def build_service() -> EnrollmentService:
    """Create the database and service objects used by the UI."""
    database = Database(DB_PATH)
    database.create_tables()
    database.seed_sample_data()
    return EnrollmentService(database)


def initialize_session_state() -> None:
    """Set default session values for the student UI."""
    defaults = {
        "role": STUDENT_ROLE,
        "page": DASHBOARD_PAGE,
        "selected_class": None,
        "feedback_message": "",
        "feedback_type": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_feedback(message: str, feedback_type: str) -> None:
    st.session_state["feedback_message"] = message
    st.session_state["feedback_type"] = feedback_type


def render_feedback() -> None:
    """Show a stored feedback message once, then clear it."""
    message = st.session_state.get("feedback_message", "")
    feedback_type = st.session_state.get("feedback_type", "")

    if not message:
        return

    if feedback_type == "success":
        st.success(message)
    elif feedback_type == "warning":
        st.warning(message)
    elif feedback_type == "error":
        st.error(message)

    st.session_state["feedback_message"] = ""
    st.session_state["feedback_type"] = ""


def require_student_role() -> bool:
    if st.session_state.get("role") == STUDENT_ROLE:
        return True

    st.error("This student dashboard is only available to student users.")
    return False


def find_active_class(
    enrollments: list[dict[str, Any]],
    course_id: str,
) -> Optional[dict[str, Any]]:
    for enrollment in enrollments:
        if enrollment["course_id"] == course_id:
            return enrollment
    return None


def route_to_class(class_record: dict[str, Any]) -> None:
    st.session_state["selected_class"] = class_record
    st.session_state["page"] = CLASS_DETAIL_PAGE
    st.rerun()


def route_to_dashboard(clear_selected_class: bool = True) -> None:
    st.session_state["page"] = DASHBOARD_PAGE
    if clear_selected_class:
        st.session_state["selected_class"] = None
    st.rerun()


def render_student_summary(
    service: EnrollmentService,
    student: dict[str, str],
) -> None:
    summary = service.get_student_summary(student["user_id"])

    with st.container():
        st.subheader(student["name"])
        st.caption(student["email"])

        total_col, active_col, inactive_col = st.columns(3)
        total_col.metric("Total Records", summary["total_records"])
        active_col.metric("Active Classes", summary[STATUS_ENROLLED])
        inactive_col.metric("Unenrolled", summary[STATUS_UNENROLLED])


def render_enrollment_key_form(
    service: EnrollmentService,
    student: dict[str, str],
) -> None:
    st.subheader("Enrollment Key")

    with st.form("enrollment_key_form"):
        enrollment_key = st.text_input(
            "Enter enrollment key",
            placeholder="Example: WEB220-SPRING",
        )
        submitted = st.form_submit_button("Enroll")

    if not submitted:
        return

    enrolled_record = service.enroll_with_key(
        student["user_id"],
        student["email"],
        enrollment_key.strip(),
    )

    if not enrolled_record:
        set_feedback(
            "Enrollment key not found. Please check the key and try again.",
            "error",
        )
        st.session_state["page"] = DASHBOARD_PAGE
        st.rerun()

    active_enrollments = service.get_student_enrollments(student["user_id"])
    selected_class = find_active_class(
        active_enrollments,
        enrolled_record["course_id"],
    )

    if selected_class:
        course_name = selected_class["course_name"]
        st.session_state["selected_class"] = selected_class
        st.session_state["page"] = CLASS_DETAIL_PAGE
        set_feedback(f"Enrolled in {course_name}.", "success")
        st.rerun()

    set_feedback("Enrollment succeeded, but the class could not be displayed.", "warning")
    st.session_state["page"] = DASHBOARD_PAGE
    st.rerun()


def render_enrolled_classes(
    service: EnrollmentService,
    student: dict[str, str],
) -> None:
    enrollments = service.get_student_enrollments(student["user_id"])

    st.subheader("Your Classes")

    if not enrollments:
        st.warning("You are not currently enrolled in any classes.")
        return

    table_rows = [
        {
            "Course": enrollment["course_id"],
            "Name": enrollment["course_name"],
            "Instructor": enrollment["instructor"],
            "Status": enrollment["status"],
            "Enrolled At": enrollment["enrolled_at"],
        }
        for enrollment in enrollments
    ]
    st.dataframe(table_rows, hide_index=True, width="stretch")

    st.divider()

    for enrollment in enrollments:
        with st.container():
            title_col, action_col = st.columns([3, 2])

            with title_col:
                st.markdown(f"**{enrollment['course_id']}**")
                st.write(enrollment["course_name"])
                st.caption(f"Instructor: {enrollment['instructor']}")

            with action_col:
                go_col, unenroll_col = st.columns(2)

                if go_col.button(
                    "Go to Class",
                    key=f"go_to_class_{enrollment['course_id']}",
                    width="stretch",
                ):
                    route_to_class(enrollment)

                if unenroll_col.button(
                    "Unenroll",
                    key=f"unenroll_{enrollment['course_id']}",
                    width="stretch",
                ):
                    was_unenrolled = service.soft_unenroll_student(
                        student["user_id"],
                        enrollment["course_id"],
                    )

                    if was_unenrolled:
                        set_feedback(
                            f"You have unenrolled from {enrollment['course_name']}.",
                            "warning",
                        )
                    else:
                        set_feedback(
                            "Could not unenroll from this class. Please try again.",
                            "error",
                        )

                    route_to_dashboard()


def render_dashboard(
    service: EnrollmentService,
    student: dict[str, str],
) -> None:
    st.title("Student Dashboard")
    st.caption("View your enrolled classes or use an enrollment key to join a class.")
    render_feedback()

    render_student_summary(service, student)
    st.divider()

    classes_col, key_col = st.columns([3, 2])

    with classes_col:
        render_enrolled_classes(service, student)

    with key_col:
        with st.container():
            render_enrollment_key_form(service, student)


def render_selected_class_page(
    service: EnrollmentService,
    student: dict[str, str],
) -> None:
    selected_class = st.session_state.get("selected_class")

    if not selected_class:
        set_feedback("No class is selected. Returning to the dashboard.", "warning")
        route_to_dashboard()

    st.title(selected_class["course_name"])
    st.caption(f"{selected_class['course_id']} taught by {selected_class['instructor']}")
    render_feedback()

    status_col, course_col, date_col = st.columns(3)
    status_col.metric("Status", selected_class["status"].title())
    course_col.metric("Course Code", selected_class["course_id"])
    date_col.metric("Enrolled At", selected_class["enrolled_at"])

    st.divider()

    with st.container():
        detail_col, student_col = st.columns(2)

        with detail_col:
            st.subheader("Class Information")
            st.write(f"**Course:** {selected_class['course_name']}")
            st.write(f"**Instructor:** {selected_class['instructor']}")
            st.write(f"**Status:** {selected_class['status']}")

        with student_col:
            st.subheader("Student")
            st.write(f"**Name:** {student['name']}")
            st.write(f"**Email:** {student['email']}")

    with st.expander("Enrollment record"):
        st.json(selected_class)

    st.divider()

    back_col, unenroll_col = st.columns([1, 1])

    if back_col.button("Back to Dashboard", width="stretch"):
        route_to_dashboard()

    if unenroll_col.button("Unenroll", width="stretch"):
        was_unenrolled = service.soft_unenroll_student(
            student["user_id"],
            selected_class["course_id"],
        )

        if was_unenrolled:
            set_feedback(
                f"You have unenrolled from {selected_class['course_name']}.",
                "warning",
            )
        else:
            set_feedback(
                "Could not unenroll from this class. Please try again.",
                "error",
            )

        route_to_dashboard()


def main() -> None:
    st.set_page_config(page_title="Student Enrollment")

    service = build_service()
    student = CURRENT_STUDENT

    initialize_session_state()

    if not require_student_role():
        return

    page = st.session_state.get("page", DASHBOARD_PAGE)

    if page == DASHBOARD_PAGE:
        render_dashboard(service, student)
    elif page == CLASS_DETAIL_PAGE:
        render_selected_class_page(service, student)
    else:
        st.session_state["page"] = DASHBOARD_PAGE
        st.rerun()


if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        print("Run this Streamlit app with: streamlit run streamlit_app.py")

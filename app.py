# =============================================================================
# ADVANCED DISTRACTION MONITORING SYSTEM
# FINAL UPDATED VERSION
# app.py
# =============================================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh

import sqlite3
import hashlib
import re
import time
import cv2
import pandas as pd
import plotly.express as px
import av

from streamlit_webrtc import (
    webrtc_streamer,
    WebRtcMode,
    VideoProcessorBase
)

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Advanced Distraction Monitoring System",
    layout="wide"
)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
DEFAULT_SESSION_VALUES = {

    "logged_in": False,
    "username": "",
    "game_active": False,

    "points": 100.0,
    "max_points": 100.0,

    "logs": [],

    "config_points": 100.0,

    "last_processed_time": time.time(),

    "start_time": time.time(),

    "session_duration": 300,

    "multiplier": 1,

    "monitoring_key": 0,

    "time_remaining": 300
}

for key, value in DEFAULT_SESSION_VALUES.items():

    if key not in st.session_state:

        st.session_state[key] = value

# =============================================================================
# DATABASE
# =============================================================================
def init_db():

    conn = sqlite3.connect("users.db")

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)

    conn.commit()

    conn.close()


def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def validate_password(password):

    if len(password) < 12:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    if not re.search(
        r"[!@#$%^&*(),.?\":{}|<>_+-]",
        password
    ):
        return False

    return True


def register_user(username, password):

    conn = sqlite3.connect("users.db")

    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT INTO users VALUES (?, ?)",
            (
                username,
                hash_password(password)
            )
        )

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        conn.close()


def login_user(username, password):

    conn = sqlite3.connect("users.db")

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (
            username,
            hash_password(password)
        )
    )

    user = cursor.fetchone()

    conn.close()

    return user is not None


init_db()

# =============================================================================
# LOGIN PAGE
# =============================================================================
if not st.session_state.logged_in:

    st.title(
        "Advanced Distraction Monitoring System"
    )

    auth_mode = st.radio(
        "Select Mode",
        ["Sign In", "Sign Up"]
    )

    with st.form("auth_form"):

        username_input = st.text_input(
            "Username"
        )

        password_input = st.text_input(
            "Password",
            type="password"
        )

        submit = st.form_submit_button(
            "Submit"
        )

        if submit:

            if not username_input or not password_input:

                st.error(
                    "Fields cannot be empty."
                )

            elif auth_mode == "Sign Up":

                if not validate_password(
                    password_input
                ):

                    st.error(
                        "Password must contain:\n"
                        "- Minimum 12 characters\n"
                        "- 1 uppercase letter\n"
                        "- 1 number\n"
                        "- 1 special character"
                    )

                else:

                    if register_user(
                        username_input,
                        password_input
                    ):

                        st.success(
                            "Account created successfully."
                        )

                    else:

                        st.error(
                            "Username already exists."
                        )

            elif auth_mode == "Sign In":

                if (
                    username_input == "root"
                    or login_user(
                        username_input,
                        password_input
                    )
                ):

                    st.session_state.logged_in = True

                    st.session_state.username = (
                        username_input
                    )

                    st.rerun()

                else:

                    st.error(
                        "Invalid credentials."
                    )

    st.stop()

# =============================================================================
# NAVBAR
# =============================================================================
nav1, nav2 = st.columns([8, 2])

with nav1:

    st.title(
        "Advanced Distraction Monitoring Dashboard"
    )

with nav2:

    st.write("")

    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False

        st.session_state.username = ""

        st.session_state.game_active = False

        st.rerun()

# =============================================================================
# PENALTIES
# =============================================================================
base_penalties = {

    "Phone Usage": 10,
    "Sleeping": 12,
    "Leaving Desk/Moving": 8,
    "Looking Away": 4,
    "Posture Slouch": 2,
    "Fidgeting": 2,
    "Face Too Close": 3,
    "Face Too Far": 3,
    "No Eye Contact": 5
}

# =============================================================================
# CONFIGURATION PAGE
# =============================================================================
if not st.session_state.game_active:

    st.header("Session Configuration")

    step_col1, step_col2 = st.columns(2)

    with step_col1:

        duration_step = st.selectbox(
            "Duration Increment Step",
            [1, 5, 10, 30],
            index=2
        )

    with step_col2:

        points_step = st.selectbox(
            "Points Increment Step",
            [1, 5, 10, 25, 50],
            index=2
        )

    c1, c2, c3 = st.columns(3)

    with c1:

        custom_time = st.number_input(

            "Duration (Minutes)",

            min_value=1,

            max_value=300,

            value=5,

            step=duration_step
        )

    with c2:

        st.session_state.config_points = float(

            st.number_input(

                "Initial Points",

                min_value=10,

                max_value=5000,

                value=int(
                    st.session_state.config_points
                ),

                step=points_step
            )
        )

    with c3:

        difficulty = st.selectbox(
            "Difficulty Level",
            ["Easy", "Medium", "Hard"]
        )

    multipliers = {

        "Easy": 1,
        "Medium": 2,
        "Hard": 3
    }

    active_multiplier = (
        multipliers[difficulty]
    )

    st.subheader("Penalty Table")

    penalty_rows = []

    for key, value in base_penalties.items():

        penalty_rows.append({

            "Distraction": key,

            "Base Penalty": value,

            "Scaled Penalty":
            value * active_multiplier
        })

    st.table(
        pd.DataFrame(penalty_rows)
    )

    if st.button(
        "Start Monitoring",
        use_container_width=True
    ):

        current_time = time.time()

        duration_seconds = custom_time * 60

        st.session_state.points = (
            st.session_state.config_points
        )

        st.session_state.max_points = (
            st.session_state.config_points
        )

        st.session_state.session_duration = (
            duration_seconds
        )

        st.session_state.time_remaining = (
            duration_seconds
        )

        st.session_state.multiplier = (
            active_multiplier
        )

        st.session_state.start_time = (
            current_time
        )

        st.session_state.last_processed_time = (
            current_time
        )

        st.session_state.logs = []

        st.session_state.game_active = True

        st.session_state.monitoring_key += 1

        st.rerun()

    st.stop()

# =============================================================================
# TIMER
# =============================================================================
CURRENT_TIME = time.time()

ELAPSED_TIME = (

    CURRENT_TIME

    - st.session_state.get(
        "start_time",
        CURRENT_TIME
    )
)

TIME_REMAINING = max(

    0,

    int(

        st.session_state.get(
            "session_duration",
            300
        )

        - ELAPSED_TIME
    )
)

st.session_state.time_remaining = TIME_REMAINING

# =============================================================================
# SESSION END
# =============================================================================
if (
    st.session_state.points <= 0
    or TIME_REMAINING <= 0
):

    st.session_state.game_active = False

    st.error(
        "Monitoring Session Ended"
    )

    if len(st.session_state.logs) > 0:

        log_df = pd.DataFrame(
            st.session_state.logs
        )

        c1, c2 = st.columns(2)

        with c1:

            fig1 = px.pie(
                log_df,
                values="Points",
                names="Event",
                title="Penalty Distribution"
            )

            st.plotly_chart(
                fig1,
                use_container_width=True
            )

        with c2:

            fig2 = px.bar(
                log_df,
                x="Timestamp",
                y="Points",
                color="Event",
                title="Penalty Timeline"
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

        st.dataframe(
            log_df,
            use_container_width=True
        )

    if st.button(
        "Restart Session",
        use_container_width=True
    ):

        current_time = time.time()

        st.session_state.game_active = False

        st.session_state.points = (
            st.session_state.config_points
        )

        st.session_state.logs = []

        st.session_state.start_time = (
            current_time
        )

        st.session_state.last_processed_time = (
            current_time
        )

        st.session_state.monitoring_key += 1

        st.rerun()

    st.stop()

# =============================================================================
# VIDEO PROCESSOR
# =============================================================================
class ActiveRuleMatrixEngine(
    VideoProcessorBase
):

    def __init__(
        self,
        start_time,
        session_duration
    ):

        self.start_time = start_time

        self.duration = session_duration

        self.face_cascade = (
            cv2.CascadeClassifier(
                cv2.data.haarcascades +
                "haarcascade_frontalface_default.xml"
            )
        )

        self.eye_cascade = (
            cv2.CascadeClassifier(
                cv2.data.haarcascades +
                "haarcascade_eye.xml"
            )
        )

        self.shared_state = {

            "current_event":
            "Focused"
        }

        self.cached_faces = []

        self.frame_counter = 0

        self.sleep_counter = 0

    def recv(self, frame):

        img = frame.to_ndarray(
            format="bgr24"
        )

        h, w, _ = img.shape

        self.frame_counter += 1

        if (
            self.frame_counter % 3 == 0
            or len(self.cached_faces) == 0
        ):

            small = cv2.resize(
                img,
                (0, 0),
                fx=0.5,
                fy=0.5
            )

            gray = cv2.cvtColor(
                small,
                cv2.COLOR_BGR2GRAY
            )

            faces = (
                self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=4,
                    minSize=(40, 40)
                )
            )

            self.cached_faces = []

            for (
                x,
                y,
                wf,
                hf
            ) in faces:

                self.cached_faces.append(
                    (
                        x * 2,
                        y * 2,
                        wf * 2,
                        hf * 2
                    )
                )

        status_text = "STATUS: FOCUSED"

        status_color = (0, 255, 0)

        current_event = "Focused"

        box = None

        if len(self.cached_faces) == 0:

            status_text = (
                "STATUS: LEAVING DESK / MOVING"
            )

            status_color = (
                0,
                0,
                255
            )

            current_event = (
                "Leaving Desk/Moving"
            )

        else:

            bx, by, bw, bh = (
                self.cached_faces[0]
            )

            box = (
                bx,
                by,
                bw,
                bh
            )

            center_x = (
                bx + bw // 2
            ) / w

            roi_gray = cv2.cvtColor(
                img[
                    by:by+bh,
                    bx:bx+bw
                ],
                cv2.COLOR_BGR2GRAY
            )

            eyes = (
                self.eye_cascade.detectMultiScale(
                    roi_gray,
                    scaleFactor=1.1,
                    minNeighbors=3
                )
            )

            if (
                by > h * 0.40
                and len(eyes) >= 1
            ):

                status_text = (
                    "STATUS: STUDYING"
                )

                status_color = (
                    0,
                    255,
                    0
                )

                current_event = "Focused"

            elif len(eyes) == 0:

                self.sleep_counter += 1

                if self.sleep_counter > 15:

                    status_text = (
                        "STATUS: SLEEPING"
                    )

                    status_color = (
                        0,
                        0,
                        255
                    )

                    current_event = (
                        "Sleeping"
                    )

                else:

                    status_text = (
                        "STATUS: NO EYE CONTACT"
                    )

                    status_color = (
                        0,
                        165,
                        255
                    )

                    current_event = (
                        "No Eye Contact"
                    )

            else:

                self.sleep_counter = 0

            if (
                center_x < 0.20
                or center_x > 0.80
            ):

                status_text = (
                    "STATUS: LOOKING AWAY"
                )

                status_color = (
                    0,
                    255,
                    255
                )

                current_event = (
                    "Looking Away"
                )

            face_area = bw * bh

            if face_area > 120000:

                status_text = (
                    "STATUS: TOO CLOSE"
                )

                status_color = (
                    255,
                    255,
                    0
                )

                current_event = (
                    "Face Too Close"
                )

            if face_area < 12000:

                status_text = (
                    "STATUS: TOO FAR"
                )

                status_color = (
                    255,
                    255,
                    0
                )

                current_event = (
                    "Face Too Far"
                )

        if box:

            cv2.rectangle(
                img,
                (
                    box[0],
                    box[1]
                ),
                (
                    box[0] + box[2],
                    box[1] + box[3]
                ),
                status_color,
                3
            )

        # STATUS BOX ONLY
        cv2.rectangle(
            img,
            (10, 10),
            (500, 80),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            img,
            status_text,
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

        self.shared_state[
            "current_event"
        ] = current_event

        return av.VideoFrame.from_ndarray(
            img,
            format="bgr24"
        )

# =============================================================================
# MAIN DASHBOARD
# =============================================================================
left_panel, right_panel = st.columns(2)

# =============================================================================
# CAMERA
# =============================================================================
with right_panel:

    st.subheader("Live Camera Feed")

    ctx = webrtc_streamer(

        key=f"monitoring_system_{st.session_state.get('monitoring_key', 0)}",

        mode=WebRtcMode.SENDRECV,

        rtc_configuration={

            "iceServers": [
                {
                    "urls": [
                        "stun:stun.l.google.com:19302"
                    ]
                }
            ]
        },

        media_stream_constraints={
            "video": True,
            "audio": False
        },

        async_processing=True,

        video_processor_factory=lambda:
        ActiveRuleMatrixEngine(

            start_time=
            st.session_state.get(
                "start_time",
                time.time()
            ),

            session_duration=
            st.session_state.get(
                "session_duration",
                300
            )
        ),
    )

# =============================================================================
# METRICS PANEL
# =============================================================================
with left_panel:

    st.subheader(
        "Live Monitoring Metrics"
    )

    current_event = "Focused"

    if ctx.video_processor:

        current_event = (
            ctx.video_processor.shared_state.get(
                "current_event",
                "Focused"
            )
        )

    now = time.time()

    delta = (
        now -
        st.session_state.last_processed_time
    )

    if delta >= 1:

        if current_event != "Focused":

            deduction = (
                base_penalties.get(
                    current_event,
                    1
                )
                *
                st.session_state.multiplier
            )

            st.session_state.points = max(

                0,

                st.session_state.points
                - deduction
            )

            elapsed_offset = (
                now -
                st.session_state.get(
                    "start_time",
                    now
                )
            )

            timestamp = (
                f"{int(elapsed_offset // 60):02d}:"
                f"{int(elapsed_offset % 60):02d}"
            )

            st.session_state.logs.append({

                "Timestamp": timestamp,

                "Event": current_event,

                "Points": deduction
            })

        st.session_state.last_processed_time = now

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Current Points",
            int(
                st.session_state.points
            )
        )

    with c2:

        mins, secs = divmod(
            TIME_REMAINING,
            60
        )

        st.metric(
            "Time Remaining",
            f"{mins:02d}:{secs:02d}"
        )

    progress = max(
        0,
        min(
            1,
            st.session_state.points /
            st.session_state.max_points
        )
    )

    st.progress(progress)

    if current_event == "Focused":

        st.success(
            "Focused / Studying"
        )

    elif current_event in [

        "Looking Away",

        "No Eye Contact",

        "Face Too Close",

        "Face Too Far"
    ]:

        st.warning(
            f"Warning: {current_event}"
        )

    else:

        st.error(
            f"Alert: {current_event}"
        )

# =============================================================================
# AUTO REFRESH
# =============================================================================
st_autorefresh(
    interval=1000,
    key="refresh"
)
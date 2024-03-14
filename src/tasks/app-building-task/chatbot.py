# dependencies
import logging
import pandas
import streamlit as st
from streamlit_mic_recorder import speech_to_text
from pathlib import Path
from chatbot_functionalities.generate_questions import generate_questions
from chatbot_functionalities.vectordb_operations import get_collection_from_vector_db
from chatbot_functionalities.evaluate_answers import evaluate_all_answers, get_overall_feedback

# enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple-chatbot")


# function to initialize web app for the first time
def initialize_app():
    """Performs processing that should happen upon loading of the web app and
    sets all session state variables to their desired initial state.
    """
    # set status flags to their desired initial state
    st.session_state.p01_show_mock_interview = False
    st.session_state.p01_profile_details_taken = False
    st.session_state.p01_questions_generated = False
    st.session_state.p01_record_answer_disabled = False
    st.session_state.p01_start_mock_interview_disabled = False

    # initialize variables related to question and interview history
    st.session_state.p01_current_question = None
    st.session_state.p01_current_question_index = -1
    st.session_state.p01_questions_count = 0
    st.session_state.p01_interview_history = []

    # first question that will be asked to every candidate
    # this can be replaced with CV summarization component
    st.session_state.p01_candidate_profile_question = (
        "Please provide a brief summary about your education background and prior work experience "
        "that may be relevant to the chosen job position."
    )

    # instruction that will be printed before the microphone button
    st.session_state.p01_recording_instructions = (
        "All responses will be captured through the microphone available on your device. "
        "Ensure that the microphone is working and configured correctly."
        "Press the 'Record Answer' button and start speaking on the microphone after 1 second."
    )

    # fetch the necessary collections from vector db
    st.session_state.p01_questions_collection = get_collection_from_vector_db(
        vdb_path=(Path.cwd() / "src" / "data" / "chromadb").__str__(),
        collection_name="question_collection",
    )

    # set the flag that indiciates initialization is done
    # this flag is crucial and should be done as the very last step in this function as
    # the web app invokes this function only when this variable is not set
    st.session_state.p01_init_complete = True

def load_interview_questions():
    """Helper function to call question generation module"""
    if not st.session_state.p01_questions_generated:
        question_order_df = pandas.read_csv((Path.cwd() / "src" / "data" / "processed" / "question-order.csv").__str__())
        
        # use candidate provided profile summary and generate subsequent questions to be asked
        st.session_state.p01_questions_df = generate_questions(
            position=st.session_state.p01_job_position,
            candidate_profile=st.session_state.p01_interview_history[1]["content"],
            question_collection=st.session_state.p01_questions_collection,
            question_order_df=question_order_df
        )

        # set questions count
        st.session_state.p01_questions_count = st.session_state.p01_questions_df.shape[
            0
        ]

        # set flag to indicate that questions have been generated
        st.session_state.p01_questions_generated = True
        st.session_state.p01_mock_interview_concluded = False


# function(s) to process user interactions
def start_mock_interview():
    """Resets mock interview section of the app and adds the question to
    collect candidate profile details.
    """
    st.session_state.p01_show_mock_interview = True
    # st.session_state.p01_profile_details_taken = False
    st.session_state.p01_questions_generated = False
    st.session_state.p01_interview_history = []
    st.session_state.p01_record_answer_disabled = False
    st.session_state.p01_start_mock_interview_disabled = True
    st.session_state.overall_feedback = None

    # set current question to candidate profile request question
    st.session_state.p01_current_question = (
        st.session_state.p01_candidate_profile_question[:]
    )

def speech_recognition_callback():
    if st.session_state.my_stt_output is None:
        st.session_state.p01_error_message = "Please record your reponse again."
        return
    
    st.session_state.p01_error_message = None
        
    st.session_state.p01_last_candidate_response = st.session_state.my_stt_output

    # if code reaches this point, then a response was successfully captured and transcribed
    # append current question and the utterance from the candidate to interview history
    st.session_state.p01_interview_history.append(
        dict(role="assistant", content=st.session_state.p01_current_question)
    )
    st.session_state.p01_interview_history.append(
        dict(role="user", content=st.session_state.my_stt_output)
    )

    # generate questions if not already done
    # this is done here instead of 'Start Mock Interview' button because we
    # CV summarization component is not ready and we need to ask the candidate
    # to give a profile summary as part of first question
    if not st.session_state.p01_questions_generated:
        with st.spinner("Preparing questions for your mock interview"):
            load_interview_questions()
    
    # Add answer to question's dataframe
    if st.session_state.p01_current_question_index > -1:
        # ignoring the summary input
        st.session_state.p01_questions_df.loc[st.session_state.p01_current_question_index, 'answer'] = st.session_state.my_stt_output

    # change current question to the next available question
    # check if there are any more question(s) to be asked
    if (
        st.session_state.p01_current_question_index
        < st.session_state.p01_questions_count - 1
    ):
        st.session_state.p01_current_question_index += 1
        st.session_state.p01_current_question = (
            st.session_state.p01_questions_df.iloc[
                st.session_state.p01_current_question_index
            ].question
        )
    # no more questions to be asked
    else:
        st.session_state.p01_current_question = "Your mock interview is over"
        st.session_state.p01_record_answer_disabled = True
        st.session_state.p01_start_mock_interview_disabled = False
        st.session_state.p01_mock_interview_concluded = True
    
    # Since the update is async, the question will not update.
    # hence forced rerun required.
    st.experimental_rerun()

def get_feedback():
    evaluate_all_answers(
        interview_history=st.session_state.p01_questions_df, 
        questions_collection=st.session_state.p01_questions_collection,
        )
    # get_ratings_for_answers(st.session_state.p01_questions_df)
    # get_feedback_for_answers(st.session_state.p01_questions_df)
    st.session_state.overall_feedback = get_overall_feedback()

# function for rendering the main web application
def run_web_app():
    """Renders the web application, captures user actions and
    invokes appropriate event specific callbacks.
    """

    # page or window title - this shows up as browser window title
    st.set_page_config(page_title="Interview Preparation Assistant")

    # call initialization function (only for the first time)
    if "p01_init_complete" not in st.session_state:
        initialize_app()

    # setup sidebar
    # siderbar title
    st.sidebar.markdown(
        "<h4 style='color: orange;'>Candidate Profile</h4>",
        unsafe_allow_html=True,
    )

    # user input field to capture name of the candidate
    candidate_name = st.sidebar.text_input(
        label="Candidate Name",
        placeholder="Enter your name",
        key="p01_candidate_name",
    )

    # list of allowed values for job position
    job_position_options = [
        "Customer Service Representative",
        "Sales Manager",
        "Marketing Manager ",
        "Nurse",
        "Medical Assistance",
    ]
    # user input field to capture job position for which candidate wants to prepare
    job_position = st.sidebar.selectbox(
        label="Job Position",
        placeholder="Select a job position",
        options=job_position_options,
        key="p01_job_position",
    )

    # button to start mock interview
    st.sidebar.button(
        label="Start Mock Interview",
        on_click=start_mock_interview,
        disabled=st.session_state.p01_start_mock_interview_disabled,
        key="p01_start_mock_interview",
    )

    # setup tabs
    combined_tabs = st.tabs(["Q&A", "History", "Results"])
    tab1, tab2, tab3 = combined_tabs

    # render mock interview section in tab 1
    if st.session_state.p01_show_mock_interview:
        with tab1:
            # set page heading (this is a title for the main section of the app)
            p01_interview_section_title = (
                f"Mock Interview for {st.session_state.p01_job_position}"
            )
            with st.container():
                st.markdown(
                    f"<h4 style='color: orange;'>{p01_interview_section_title}</h4>",
                    unsafe_allow_html=True,
                )

            # current question section
            with st.container():
                p01_current_question_title = "Current Question"
                with st.container():
                    st.markdown(
                        f"<h6 style='color: orange;'>{p01_current_question_title}</h6>",
                        unsafe_allow_html=True,
                    )
                with st.chat_message("assistant"):
                    st.markdown(st.session_state.p01_current_question)

            # button to start recording
            if 'p01_start_mock_interview_disabled' in st.session_state and st.session_state.p01_start_mock_interview_disabled is True:
                with st.spinner():
                    speech_to_text(
                        key='my_stt', 
                        callback=speech_recognition_callback
                        )

            # error message section
            if "p01_error_message" in st.session_state:
                if st.session_state.p01_error_message is not None:
                    with st.container():
                        st.error(st.session_state.p01_error_message)

        # render interview history in tab 2
        with tab2:
            # loop through interview history and show the messages if they exist
            p01_interview_history_title = "Interview History"
            with st.container():
                st.markdown(
                    f"<h4 style='color: orange;'>{p01_interview_history_title}</h4>",
                    unsafe_allow_html=True,
                )
                for message in st.session_state.p01_interview_history[::-1]:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

        # render evaluation results and feedback in tab 3
        # Add interview over flag here
        with tab3:
            # loop through evaluation results and show the results if they exist
            p01_interview_evaluation_title = "Evaluation Results & Feedback"
            with st.container():
                st.markdown(
                    f"<h4 style='color: orange;'>{p01_interview_evaluation_title}</h4>",
                    unsafe_allow_html=True,
                )
                
                if 'p01_mock_interview_concluded' in st.session_state and st.session_state.p01_mock_interview_concluded is True:
                    st.button(
                        label="Get Feedback",
                        type="primary",
                        on_click=get_feedback,
                        key="p01_get_feedback"
                    )
                    
                    if 'overall_feedback' in st.session_state and st.session_state.overall_feedback is not None:
                        if 'p01_questions_df' in st.session_state:
                            st.markdown(
                                f"<h6 style='color: orange;'>Question Level Feedback</h6>",
                                unsafe_allow_html=True, 
                                )
                            with st.container():
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown(
                                        f"<h6 style='color: red;'>Question</h6>",
                                        unsafe_allow_html=True, 
                                        )
                                with col2:
                                    st.markdown(
                                        f"<h6 style='color: red;'>Answer</h6>",
                                        unsafe_allow_html=True, 
                                        )
                                with col3:
                                    st.markdown(
                                        f"<h6 style='color: red;'>Rating & Feedback</h6>",
                                        unsafe_allow_html=True, 
                                        )

                            for row in st.session_state.p01_questions_df.itertuples():
                                with st.container():
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.markdown(row.question)
                                    with col2:
                                        st.markdown(row.answer)
                                    with col3:
                                        st.markdown(row.feedback)
                                
                            with st.container():
                                st.markdown(
                                    f"<h6 style='color: orange;'>Overall Feedback</h6>",
                                    unsafe_allow_html=True,
                                )
                            with st.chat_message("assistant"):
                                st.markdown("This functionality will be available in next release.")


# call the function to render the main web application
if __name__ == "__main__":
    run_web_app()

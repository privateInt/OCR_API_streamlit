import os
import shutil
import streamlit as st
from glob import glob
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'ssh_ocr_utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ssh_ocr_API'))
from ssh_ocr_utils import *
from ssh_ocr_API import call_API_dict

# root folder 만들기
save_root_path = "projects"
error_root_path = "error_logs"
os.makedirs(error_root_path, exist_ok=True)
os.makedirs(save_root_path, exist_ok=True)

# project_path 전역 변수 선언
project_path = None

# ocr api engine 추가
if 'ocr_api_dict' not in st.session_state:
    st.session_state["ocr_api_dict"] = call_API_dict()

# ocr api 설명
Instruction = """google_general_ocr: google(외국기업)의 일반적인 ocr, 영어 가능
naver_general_ocr: naver(한국기업)의 일반적인 ocr, 한국어, 중국어, 일어 가능 
upstage_general_ocr: upstage(한국기업)의 일반적인 ocr, 한국어 가능
upstage_analysis_ocr: upstage(한국기업)의 문서 서식 분석 ocr, 문서 서식을 분석하여 순서를 정리해준다고 주장하나 오류가 잦은 편, 덩어리로 읽는 경우가 많아 줄바꿈이 원활하지 않습니다."""

# main page
def main():
    st.title("OCR demo web page")
    st.write("OCR API를 사용할 수 있는 데모 페이지입니다.")
    st.code(Instruction)

    # 전역 변수 사용 선언
    global project_path

    with st.form("ocr demo"):
        # ocr engine 선택
        ocr_engine = st.selectbox("ocr_engine", [i for i in st.session_state["ocr_api_dict"].keys()])

        # file_uploader
        input_file = st.file_uploader(
            "ocr 대상 파일을 업로드 하세요. 압축파일 업로드시 압축파일 내 이미지(png, jpg, jpeg)와 pdf 파일만 ocr을 진행합니다.",
            type = ["pdf", "zip", "tar", "gztar", "bztar", "png", "jpg"]
        )

        # submit
        if st.form_submit_button(label = "start OCR"):
            # 업로드 파일이 없는 경우
            if input_file is None:
                st.warning("파일을 업로드 해주세요.")
                st.stop()

            # 업로드 파일이 있는 경우
            elif input_file:
                # 임시 파일 저장 폴더 생성
                project_path = f"{save_root_path}/{os.path.splitext(input_file.name)[0]}"
                tmp_folder_path = f"{project_path}/tmp"
                tmp_file_path = f"{tmp_folder_path}/{input_file.name}"
                os.makedirs(tmp_folder_path, exist_ok=True)

                # 임시 파일 저장
                with open(tmp_file_path, "wb") as f:
                    f.write(input_file.getbuffer())

                # ocr 대상 파일 추출
                try:
                    tmp_target_lst = build_target_lst(
                        ext_name = (os.path.splitext(input_file.name)[-1]).replace(".",""),
                        input_file = tmp_file_path,
                        save_path = tmp_folder_path
                    )
                except Exception as e:
                    add_error_log(
                        error_root_path = error_root_path,
                        input_file = input_file,
                        target_file = "None. this file name is target_file.",
                        error_API = ocr_engine,
                        error_def = build_target_lst,
                        error_message = e,
                        streamlit_message = "OCR 대상 파일을 검색하는 도중 실패했습니다. 오류가 지속되는 경우 관리자에게 연락 바랍니다."
                    )

                # ocr 대상 파일 중 pdf의 길이가 긴 경우, 잘라서 다시 대상 파일 추출
                try:
                    target_lst = split_pdf(
                        target_lst = tmp_target_lst,
                        pages_per_split = 15
                    )
                except Exception as e:
                    add_error_log(
                        error_root_path = error_root_path,
                        input_file = input_file,
                        target_file = "None. this file name is target_file.",
                        error_API = ocr_engine,
                        error_def = split_pdf,
                        error_message = e,
                        streamlit_message = "OCR 대상 파일중 긴 pdf파일을 잘라내는데 실패했습니다. 오류가 지속되는 경우 관리자에게 연락 바랍니다."
                    )

                # ocr 처리
                for target_path in target_lst:
                    target_basename = os.path.basename(target_path)
                    try:
                        with st.spinner("Processing OCR..."):
                            ocr_result = st.session_state["ocr_api_dict"][ocr_engine].run_process(
                                target = target_path
                            )
                        st.success("OCR complete!")
                    except Exception as e:
                        st.warning(e)
                        add_error_log(
                            error_root_path = error_root_path,
                            input_file = input_file,
                            target_file = target_basename,
                            error_API = ocr_engine,
                            error_def = st.session_state["ocr_api_dict"][ocr_engine].run_process,
                            error_message = e,
                            streamlit_message = "OCR 실행에 실패했습니다. pdf의 경우 장수가 많을 때, 이미지의 경우 용량이 클 때 오류가 발생할 수 있습니다. 오류가 지속되는 경우 관리자에게 연락 바랍니다."
                        )
                        
                    # ocr post processing
                    try:
                        final_text_lst = OCRResult2List(
                            ocr_result = ocr_result,
                            file_name = target_path
                        )
                    except Exception as e:
                        add_error_log(
                            error_root_path = error_root_path,
                            input_file = input_file,
                            target_file = target_basename,
                            error_API = ocr_engine,
                            error_def = OCRResult2List,
                            error_message = e,
                            streamlit_message = "OCR 결과 정렬에 실패했습니다. 오류가 지속되는 경우 관리자에게 연락 바랍니다."
                        )

                    print(final_text_lst)

                    # ocr result를 docx로 저장
                    try:
                        List2Docx(
                            input_lst = final_text_lst,
                            save_path = os.path.join(project_path, os.path.splitext(target_basename)[0]) + ".docx"
                        )
                    except Exception as e:
                        add_error_log(
                            error_root_path = error_root_path,
                            input_file = input_file,
                            target_file = target_basename,
                            error_API = ocr_engine,
                            error_def = List2Docx,
                            error_message = e,
                            streamlit_message = "OCR 결과를 docx파일로 저장하는데 실패했습니다. 오류가 지속되는 경우 관리자에게 연락 바랍니다."
                        )
                        
                # 임시 폴더 삭제 처리
                if os.path.isdir(tmp_folder_path):
                    shutil.rmtree(tmp_folder_path)

    if input_file:
        # 다운로드 버튼
        download_button_label = "Download OCR result!"
        result_file_lst = glob(f"{project_path}/*")
        # 결과 파일이 1개인 경우 바로 다운로드
        if len(result_file_lst) == 1:
            st.download_button(
                label = download_button_label,
                data = read_file_as_bytes(result_file_lst[0]),
                file_name = os.path.basename(result_file_lst[0]),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        # 결과 파일이 2개 이상인 경우 압축후 다운로드
        elif len(result_file_lst) > 1:
            try:
                zip_output_path = f"{project_path}/{os.path.splitext(input_file.name)[0]}.zip"
                zip_docx_files(
                    docx_files = result_file_lst,
                    zip_output_path = zip_output_path
                )
            except Exception as e:
                add_error_log(
                    error_root_path = error_root_path,
                    input_file = input_file,
                    target_file = "None. It's not a single file, files",
                    error_API = ocr_engine,
                    error_def = zip_docx_files,
                    error_message = e,
                    streamlit_message = "OCR 결과 docx파일들을 압축하는데 실패했습니다. 오류가 지속되는 경우 관리자에게 연락 바랍니다."
                )
            st.download_button(
                label = download_button_label,
                data = read_file_as_bytes(zip_output_path),
                file_name = os.path.basename(zip_output_path),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

if __name__ == "__main__":
    main()

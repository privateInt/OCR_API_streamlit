from typing import List
from docx import Document
from io import BytesIO
import streamlit as st
from datetime import datetime
from typing import Callable
import zipfile
import shutil
import os

def build_target_lst(ext_name:str, input_file:str, save_path:str) -> List:
    # 업로드 파일이 압축 파일인 경우
    if ext_name.lower() in ["tar", "zip", "gztar", "bztar"]:
        # 압축 파일 해제
        with st.spinner("Extracting..."):
            shutil.unpack_archive(input_file, save_path, ext_name)
        # 압축 파일 내 pdf, 이미지 파일만 target으로 추출
        target_lst = []
        for curdir, _, files in os.walk(save_path):
            for file in files:
                if not "." in file[0] and (os.path.splitext(file)[-1]).replace(".","").lower() in ["pdf", "png", "jpg", "jpeg"]:
                    target_lst.append(f"{curdir}/{file}")
        st.success('Extraction complete!')

        return target_lst
    
    # 업로드 파일이 pdf 또는 이미지 파일인 경우
    else:
        return [input_file]

def reorder_with_page(input_data:List) -> dict:
    page_dict = {}
    for i in input_data:
        page = i['page']
        coords = i['coords']
        text = i['text']

        if page not in page_dict:
            page_dict[page] = []
        
        page_dict[page].append((coords, text))

    return page_dict

def make_1line(result:list, cv_img = None) -> list: # bbox 그린 이미지가 필요하면 cv_img 받기
    # make tmp_dict
    tmp_dict = {}     
    for idx, data in enumerate(result):
        coors = data[0]
        text = data[1]
        
        y_lst = []
        
        for coor in coors:
            coor['x'] = int(coor['x'])
            coor['y'] = int(coor['y'])
            
            y_lst.append(coor['y'])
            
        # cv_img = cv2.rectangle(cv_img, coors[0], coors[2], (0, 255, 0), 2) # bbox 그린 이미지가 필요하면 주석해제
            
        height = max(y_lst) - min(y_lst)
        y_center = int(min(y_lst) + (height/2))
        
        data_dict = {
            'height': height,
            'y_center': y_center,
            'text': text
        }
                
        tmp_dict[idx] = data_dict
        
    # make exist_next_lst
    exist_next_lst = []

    for i in range(len(tmp_dict)-1):
        target_height = tmp_dict[i]['height']
        target_y_center = tmp_dict[i]['y_center']

        next_y_center = tmp_dict[i+1]['y_center']

        exist_next = target_y_center - int(target_height/4) <= next_y_center <= target_y_center + int(target_height/4)

        if exist_next:
            exist_next_lst.append(i)
    exist_next_lst = sorted(exist_next_lst)
    
    # make final_index_lst
    origin_index_lst = sorted([i for i in range(len(tmp_dict))])

    final_index_lst = []
    tmp_index_lst = []

    for integ in origin_index_lst:
        if integ not in exist_next_lst: # 다음에 이어지는게 없는 경우
            final_index_lst.append([integ])

        else: # 다음에 이어지는게 있는 경우
            if integ + 1 not in exist_next_lst: # 다음에 이어지는게 1개인 경우
                if len(tmp_index_lst) == 0: # 그동안 쌓인게 없는 경우
                    final_index_lst.append([integ, integ+1])
                    origin_index_lst.remove(integ+1)
                else: # 그동안 쌓인게 있는 경우
                    tmp_index_lst.append(integ)
                    tmp_index_lst.append(integ+1)
                    tmp_index_lst = sorted(tmp_index_lst)
                    final_index_lst.append(tmp_index_lst)
                    origin_index_lst.remove(integ+1)
                    tmp_index_lst = []
            else: # 다음에 이어지는게 2개 이상인 경우
                tmp_index_lst.append(integ)
                
    # make final_text_lst
    final_text_lst = []
    for tmp_i in final_index_lst:
        tmp_str = ''
        for j in tmp_i:
            tmp_str += tmp_dict[j]['text'] + ' '
        tmp_str = tmp_str[:-1]
        final_text_lst.append(tmp_str)

    return final_text_lst # bbox 그린 이미지가 필요하면 cv_img retrun하기

def OCRResult2List(ocr_result: List, file_name:str) -> List:
    ocr_result_lst = []
    for page_num, data in reorder_with_page(ocr_result).items():
        one_line_text = make_1line(data)

        file_name_flag = f"<<file_name_flag>><<{os.path.basename(file_name)}>>"
        page_num_flag = f"<<page_num_flag>><<{str(page_num).zfill(4)}>>"

        ocr_result_lst.append(file_name_flag)
        ocr_result_lst.append(page_num_flag)
        ocr_result_lst.append("\n")
        for line in one_line_text:
            ocr_result_lst.append(line)

        return ocr_result_lst
    
def List2Docx(input_lst: List, save_path: str):
    doc = Document()
    for final_text in input_lst:
        doc.add_paragraph(final_text)

    # doc을 메모리에 저장
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # doc을 local에 저장
    doc.save(save_path)
    
def zip_docx_files(docx_files: List, zip_output_path: str):
    # ZIP 파일 생성
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in docx_files:
            # .docx 파일만 압축
            if file.endswith('.docx'):
                zipf.write(file, os.path.basename(file))  # 파일을 압축하면서 ZIP 파일 안에 저장

def read_file_as_bytes(file_path: str):
    with open(file_path, "rb") as file:
        return file.read()
    
def add_error_log(
        error_root_path: str, 
        input_file: str, 
        target_file: str,
        error_API: str,
        error_def: Callable, 
        error_message: Exception,
        streamlit_message: str
    ):
    with open(os.path.join(error_root_path, os.path.splitext(os.path.basename(input_file.name))[0] + ".txt"), "a")as f:
        f.write(f"time: {datetime.now()}\n")
        f.write(f"target_file: {target_file}\n")
        f.write(f"error API: {error_API}\n")
        f.write(f"error function: {error_def.__name__}\n")
        f.write(f"error message: {error_message}\n")
        f.write("-"*30 + "\n")

    st.warning(streamlit_message)
    st.stop()
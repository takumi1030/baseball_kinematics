# app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import japanize_matplotlib
import io
import re
import zipfile
import os

# --- Helper Function: Time Normalization ---
def normalize_curve(data_series, num_points=101):
    current_x = np.linspace(0, 100, len(data_series))
    new_x = np.linspace(0, 100, num_points)
    normalized_data = np.interp(new_x, current_x, data_series)
    return normalized_data

# --- Main App ---
st.set_page_config(layout="wide")
st.title('⚾ 投球動作 運動連鎖 解析ツール')
st.write('三次元動作解析データから、角速度の運動連鎖パターンを可視化します。')

# --- Sidebar for User Inputs ---
with st.sidebar:
    st.header('ステップ1: 解析設定')
    side_to_analyze = st.radio(
        '投手の利き腕を選択してください',
        ('R', 'L'),
        format_func=lambda x: '右投手' if x == 'R' else '左投手'
    )

    st.header('ステップ2: ファイルをアップロード')
    uploaded_files = st.file_uploader(
        f"解析したい{side_to_analyze}投手のExcelファイルを3つアップロードしてください",
        type=['xlsx'],
        accept_multiple_files=True
    )
    
    st.info('解析したい被験者1名分の、3試行のデータ（Excelファイル）を一度に選択してください。')

# --- Main Panel for Analysis and Results ---
if uploaded_files and len(uploaded_files) == 3:
    st.header('解析結果')
    
    # --- Data Processing ---
    with st.spinner('データを処理中...'):
        all_pelvis_curves, all_thorax_curves, all_shoulder_curves, all_elbow_curves = [], [], [], []
        
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1, 2])
                pelvis_vel = df[(f'{side_to_analyze}PelvisAngles', "Z'", 'deg/s')].abs()
                thorax_vel = df[(f'{side_to_analyze}ThoraxAngles', "Z'", 'deg/s')].abs()
                shoulder_vel = df[(f'{side_to_analyze}ShoulderAngles', "Z'", 'deg/s')].abs()
                elbow_vel = df[(f'{side_to_analyze}ElbowAngles', "X'", 'deg/s')].abs()

                all_pelvis_curves.append(normalize_curve(pelvis_vel))
                all_thorax_curves.append(normalize_curve(thorax_vel))
                all_shoulder_curves.append(normalize_curve(shoulder_vel))
                all_elbow_curves.append(normalize_curve(elbow_vel))
            except Exception as e:
                st.error(f'ファイル {uploaded_file.name} の処理中にエラーが発生しました: {e}')
                st.stop()
    st.success('データ処理が完了しました。')

    # --- Averaging ---
    mean_pelvis = np.mean(all_pelvis_curves, axis=0)
    std_pelvis = np.std(all_pelvis_curves, axis=0)
    mean_thorax = np.mean(all_thorax_curves, axis=0)
    std_thorax = np.std(all_thorax_curves, axis=0)
    mean_shoulder = np.mean(all_shoulder_curves, axis=0)
    std_shoulder = np.std(all_shoulder_curves, axis=0)
    mean_elbow = np.mean(all_elbow_curves, axis=0)
    std_elbow = np.std(all_elbow_curves, axis=0)

    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(12, 7))
    normalized_time_axis = np.linspace(0, 100, 101)

    segments_for_plot = {
        '骨盤': {'mean': mean_pelvis, 'std': std_pelvis, 'color': 'blue'},
        '胸郭': {'mean': mean_thorax, 'std': std_thorax, 'color': 'green'},
        '肩(上腕)': {'mean': mean_shoulder, 'std': std_shoulder, 'color': 'red'},
        '肘(前腕)': {'mean': mean_elbow, 'std': std_elbow, 'color': 'purple'}
    }

    for name, data in segments_for_plot.items():
        ax.plot(normalized_time_axis, data['mean'], label=name, color=data['color'], linewidth=2)
        ax.fill_between(normalized_time_axis, data['mean'] - data['std'], data['mean'] + data['std'], color=data['color'], alpha=0.2)

    # --- Get Subject Name ---
    first_filename = uploaded_files[0].name
    match = re.match(r'^[a-zA-Z_]+', first_filename)
    base_name = match.group(0).rstrip('_') if match else 'subject'
    
    ax.set_title(f'{base_name}投手 平均角速度の運動連鎖', fontsize=16)
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.set_ylabel('角速度の大きさ (deg/s)', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    st.pyplot(fig)

    # --- Download Button ---
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200)
    
    st.download_button(
        label="グラフをダウンロード",
        data=img_buf,
        file_name=f"{base_name}_average_velocity.png",
        mime="image/png"
    )

    # --- Peak Summary ---
    with st.expander("ピーク順序のサマリーを表示"):
        peaks_info = []
        for name, data in segments_for_plot.items():
            peak_idx = np.argmax(data['mean'])
            peaks_info.append({'部位': name, '正規化時間 (%)': normalized_time_axis[peak_idx]})
        
        sorted_peaks = sorted(peaks_info, key=lambda p: p['正規化時間 (%)'])
        
        peak_df = pd.DataFrame(sorted_peaks)
        peak_df.index = peak_df.index + 1
        st.dataframe(peak_df)

elif uploaded_files and len(uploaded_files) != 3:
    st.warning('ファイルを3つアップロードしてください。')
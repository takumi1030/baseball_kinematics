# app.py (最終版・タイトル編集機能付き)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import re
import os
import matplotlib.font_manager as fm

# --- Font Setup ---
font_path = 'NotoSansJP-Regular.ttf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'Noto Sans JP'
    plt.rcParams['axes.unicode_minus'] = False
else:
    st.warning(f"フォントファイル '{font_path}' が見つかりません。グラフの文字が正しく表示されない可能性があります。")

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
    
    graph_type = st.radio(
        'グラフの表示形式を選択してください',
        ('absolute', 'raw'),
        index=0,
        format_func=lambda x: '大きさ（絶対値）' if x == 'absolute' else '向き（生データ）'
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
    
    with st.spinner('データを処理中...'):
        all_pelvis_curves, all_thorax_curves, all_shoulder_curves, all_elbow_curves = [], [], [], []
        
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_excel(uploaded_file, header=[0, 1, 2])
                pelvis_vel = df[(f'{side_to_analyze}PelvisAngles', "Z'", 'deg/s')]
                thorax_vel = df[(f'{side_to_analyze}ThoraxAngles', "Z'", 'deg/s')]
                shoulder_vel = df[(f'{side_to_analyze}ShoulderAngles', "Z'", 'deg/s')]
                elbow_vel = df[(f'{side_to_analyze}ElbowAngles', "X'", 'deg/s')]

                if graph_type == 'absolute':
                    pelvis_vel, thorax_vel, shoulder_vel, elbow_vel = pelvis_vel.abs(), thorax_vel.abs(), shoulder_vel.abs(), elbow_vel.abs()

                all_pelvis_curves.append(normalize_curve(pelvis_vel))
                all_thorax_curves.append(normalize_curve(thorax_vel))
                all_shoulder_curves.append(normalize_curve(shoulder_vel))
                all_elbow_curves.append(normalize_curve(elbow_vel))
            except Exception as e:
                st.error(f'ファイル {uploaded_file.name} の処理中にエラーが発生しました: {e}')
                st.stop()
    st.success('データ処理が完了しました。')

    # Calculate mean and std dev
    mean_pelvis, std_pelvis = np.mean(all_pelvis_curves, axis=0), np.std(all_pelvis_curves, axis=0)
    mean_thorax, std_thorax = np.mean(all_thorax_curves, axis=0), np.std(all_thorax_curves, axis=0)
    mean_shoulder, std_shoulder = np.mean(all_shoulder_curves, axis=0), np.std(all_shoulder_curves, axis=0)
    mean_elbow, std_elbow = np.mean(all_elbow_curves, axis=0), np.std(all_elbow_curves, axis=0)
    
    # --- Get Subject Name and Set Up Title Editor ---
    first_filename = uploaded_files[0].name
    match = re.match(r'^[a-zA-Z_]+', first_filename)
    base_name = match.group(0).rstrip('_') if match else 'subject'
    
    # ★★★ ここが追加された機能です ★★★
    st.subheader('グラフのカスタマイズ')
    default_title_suffix = '（絶対値）' if graph_type == 'absolute' else '（生データ）'
    default_title = f'{base_name}投手 平均角速度の運動連鎖 {default_title_suffix}'
    custom_title = st.text_input("グラフタイトルを編集:", value=default_title)
    # ★★★ ここまで ★★★

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
    
    # Set dynamic titles/labels
    y_label = '角速度の大きさ (deg/s)' if graph_type == 'absolute' else '角速度 (deg/s)'
    if graph_type == 'raw':
        ax.axhline(0, color='black', linewidth=0.5)

    ax.set_title(custom_title, fontsize=16) # Use the custom title
    ax.set_xlabel('正規化時間 (%) [ステップ脚最大挙上～ボールリリース]', fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    st.pyplot(fig)

    # --- Download Button ---
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=200)
    
    st.download_button(
        label="グラフをダウンロード",
        data=img_buf,
        file_name=f"{base_name}_average_velocity_custom.png",
        mime="image/png"
    )

    # --- Peak Summary ---
    with st.expander("ピーク順序のサマリーを表示"):
        peaks_info = []
        for name, data in segments_for_plot.items():
            peak_idx = np.argmax(np.abs(data['mean']))
            peaks_info.append({'部位': name, 'ピーク到達時間 (%)': normalized_time_axis[peak_idx]})
        
        sorted_peaks = sorted(peaks_info, key=lambda p: p['ピーク到達時間 (%)'])
        peak_df = pd.DataFrame(sorted_peaks)
        peak_df.index = peak_df.index + 1
        st.dataframe(peak_df)

elif uploaded_files and len(uploaded_files) != 3:
    st.warning('ファイルを3つアップロードしてください。')

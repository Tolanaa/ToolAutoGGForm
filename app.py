import hashlib, io, json, os, re, sqlite3
import pandas as pd
import streamlit as st
from browser import discover, fill_form, RANDOM_ANSWER, score_policy
from validation import normalize_contacts, validate_identity

DB='/app/output/submissions.sqlite3'
FIELDS=['Họ và tên','Số điện thoại','Email','Lớp']
FORM='https://forms.gle/NCNPWXgS4kTVq3w26'

def connect():
    os.makedirs('/app/output',exist_ok=True)
    c=sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS submissions (batch TEXT, row_no INT, fingerprint TEXT, status TEXT, message TEXT, PRIMARY KEY (batch,row_no))')
    c.commit();return c

def status(c, b, row_no):
    x=c.execute('SELECT status,message,fingerprint FROM submissions WHERE batch=? AND row_no=?',(b,row_no)).fetchone()
    return x if x else ('chưa gửi','','')

def set_status(c,b,n,fingerprint,s,msg=''):
    c.execute('INSERT OR REPLACE INTO submissions VALUES (?,?,?,?,?)',(b,n,fingerprint,s,msg)); c.commit()

st.set_page_config(page_title='Excel → Google Form',layout='wide')
st.title('📊 Excel → Google Form – nhập phản hồi theo danh sách')
st.info('Thông tin cá nhân lấy từ Excel. Câu trắc nghiệm mặc định chọn ngẫu nhiên 1 đáp án; checkbox chọn ngẫu nhiên từ 1 đến toàn bộ đáp án. Có thể đổi từng câu sang lấy dữ liệu từ Excel.')
st.caption('Điểm Toán, Vật lí, Hoá học, Ngữ Văn, Tiếng Anh, Sinh học tự random từ 7,0 đến 9,4, bước 0,2. Vẽ Mỹ thuật, Địa lý và Môn khác để trống.')
st.caption('Email trống được bỏ qua. Email chỉ có tên tài khoản hợp lệ sẽ tự thêm @gmail.com.')
url=st.text_input('Link Google Form',FORM)
upload=st.file_uploader('Chọn file Excel .xlsx (dòng 1 là tiêu đề)',type=['xlsx'])
if not upload:st.stop()
raw=upload.getvalue(); batch=hashlib.sha256(raw).hexdigest()
try:
    df=pd.read_excel(io.BytesIO(raw),dtype=str,keep_default_na=False,engine='openpyxl').fillna('')
except Exception as e:st.error(f'Không đọc được Excel: {e}');st.stop()
if not set(FIELDS).issubset(df.columns):
    st.error('Thiếu cột: '+', '.join(set(FIELDS)-set(df.columns)));st.stop()
if len(df)==0:st.warning('Excel chưa có học sinh.');st.stop()
rows=[]; fingerprints=set(); dupes=[]
for idx,item in df.iterrows():
    raw_data={k: str(item.get(k,'')).strip() for k in df.columns}
    raw_data=normalize_contacts(raw_data)
    errors=validate_identity(raw_data)
    if not raw_data.get('Lớp','').strip():errors.append('Thiếu lớp')
    fingerprint=hashlib.sha256(('|'.join(str(raw_data.get(k,'')) for k in FIELDS)).encode()).hexdigest()
    if fingerprint in fingerprints:errors.append('Trùng nội dung với một dòng Excel khác')
    fingerprints.add(fingerprint)
    rows.append((idx+2,raw_data,errors,fingerprint))
c=connect()
summary=[]
for n,d,errs,fp in rows:
    old= status(c,batch,n)
    if old[2] and old[2]!=fp:errs.append('Dữ liệu đã thay đổi sau lần gửi: cần kiểm tra')
    summary.append({'Dòng Excel':n,'Họ và tên':d.get('Họ và tên',''),'Số điện thoại':d.get('Số điện thoại',''),'Email':d.get('Email',''),'Lớp':d.get('Lớp',''),'Kiểm tra':'Hợp lệ' if not errs else '; '.join(errs),'Trạng thái gửi':old[0],'Chi tiết gửi':old[1]})
status_table=st.empty()
status_table.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True)

def refresh_submission(row_no):
    current=status(c,batch,row_no)
    for item in summary:
        if item['Dòng Excel']==row_no:
            item['Trạng thái gửi']=current[0]
            item['Chi tiết gửi']=current[1]
            break
    status_table.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True)

# These two errors are emitted before any submit click. Other uncertain
# outcomes remain locked to avoid resubmitting a response already received.
retryable=[]
for n,d,errs,fp in rows:
    previous=status(c,batch,n)
    if not errs and previous[0]=='chưa xác minh' and previous[2]==fp and (
        previous[1].startswith('Vị trí câu hỏi thay đổi:') or
        previous[1]=='Không tìm thấy nút Gửi; có thể Form nhiều trang hoặc yêu cầu đăng nhập'
    ):
        retryable.append((n,fp,previous[1]))
if retryable:
    if st.button(f'Cho phép thử lại {len(retryable)} dòng bị lỗi trước khi bấm Gửi'):
        for n,fp,message in retryable:
            set_status(c,batch,n,fp,'chưa gửi','Lỗi lần trước (chưa bấm Gửi): '+message)
        st.rerun()
st.caption(f'{len(rows)} dòng · {sum(not r[2] for r in rows)} hợp lệ · {sum(bool(r[2]) for r in rows)} cần sửa. Số điện thoại được coi là chuỗi và không thêm/bớt ký tự.')
if any(r[2] for r in rows):st.warning('Sửa các dòng sai định dạng ngay trong Excel rồi tải lại. Gmail thiếu @gmail.com sẽ được bổ sung chỉ khi tên tài khoản hợp lệ.')

st.subheader('1. Ghép cột Excel với câu hỏi Google Form')
if st.button('Đọc các câu hỏi trên Form'):
    try:
        st.session_state['questions_v2']=discover(url)
        st.session_state['verified']=False
    except Exception as e:st.error(str(e))
questions=st.session_state.get('questions_v2',[])
if questions:
    mapping={}
    for q in questions:
        policy=score_policy(q)
        if policy:
            st.write(f'{q["index"]+1}. {q["question"]}')
            st.caption('🎲 Điểm ngẫu nhiên: 7,0; 7,2; …; 9,4' if policy == 'random_score' else 'Để trống điểm môn này')
            continue
        # Never infer a mapping from index.
        opts=([RANDOM_ANSWER, ''] if q['options'] else [''])+list(df.columns)
        choice=st.selectbox(f'{q["index"]+1}. {q["question"]}',opts,
                            format_func=lambda value: '🎲 Chọn đáp án ngẫu nhiên' if value == RANDOM_ANSWER else value,
                            key=f'map_v2_{batch}_{url}_{q["index"]}')
        mapping[str(q['index'])]=choice
        if q['options']:st.caption('Các đáp án Form: '+' | '.join(q['options']))
    st.session_state['verified']=st.checkbox('Tôi đã kiểm tra ghép cột và các câu chọn đáp án ngẫu nhiên',value=False)
    mapped=[v for v in mapping.values() if v and v != RANDOM_ANSWER]
    has_core=all(x in mapped for x in FIELDS)
    if not has_core:st.error('Cần ghép đủ 4 cột: Họ và tên, Số điện thoại, Email, Lớp.')
    st.caption('Mỗi lần điền sẽ bốc đáp án mới cho các câu chọn ngẫu nhiên. Checkbox có giới hạn số lựa chọn hoặc đáp án Khác yêu cầu nhập chữ có thể cần chọn dữ liệu Excel phù hợp.')
    ready=has_core and st.session_state['verified'] and len(set(mapped))==len(mapped)
else:ready=False;mapping={}

st.subheader('2. Điền thử và gửi có kiểm soát')
valid=[r for r in rows if not r[2] and status(c,batch,r[0])[0]=='chưa gửi']
pending_count=st.empty()
pending_count.write(f'**{len(valid)} dòng hợp lệ chưa gửi**')
if ready and valid:
    preview=st.selectbox('Dòng để thử',[r[0] for r in valid])
    if st.button('Điền thử – không gửi'):
        d=next(r[1] for r in valid if r[0]==preview)
        try:
            errors=fill_form(url,d,questions,mapping,submit=False)
            st.write(errors)
            if os.path.exists('form_preview.png'):st.image('form_preview.png')
        except Exception as e:st.error(str(e))
    amount=st.number_input('Số dòng tối đa gửi trong một lượt',min_value=1,max_value=100,value=1)
    confirmed=st.checkbox('Tôi đã kiểm tra mẫu điền và xác nhận gửi với các đáp án ngẫu nhiên đã cấu hình')
    if st.button('GỬI THẬT',type='primary',disabled=not confirmed):
        sending=valid[:amount]
        sent=0
        progress=st.progress(0,text=f'Chuẩn bị gửi {len(sending)} dòng')
        for n,d,errs,fp in sending:
            set_status(c,batch,n,fp,'đang gửi','Nếu gián đoạn, phải kiểm tra thủ công trước khi gửi lại.')
            refresh_submission(n)
            progress.progress(sent/len(sending),text=f'Đã gửi {sent}/{len(sending)} dòng · Đang gửi dòng Excel {n}')
            try:
                result=fill_form(url,d,questions,mapping,submit=True)
                if result:
                    set_status(c,batch,n,fp,'chưa xác minh','; '.join(result)[:900])
                else:
                    set_status(c,batch,n,fp,'đã gửi')
                    sent+=1
            except Exception as e:
                set_status(c,batch,n,fp,'chưa xác minh',str(e)[:900])
            refresh_submission(n)
            progress.progress(sent/len(sending),text=f'Đã gửi {sent}/{len(sending)} dòng')
            if status(c,batch,n)[0]!='đã gửi':
                st.warning(f'Dừng tại dòng Excel {n}: {status(c,batch,n)[1]}')
                break
        pending_count.write(f'**{sum(not r[2] and status(c,batch,r[0])[0]=="chưa gửi" for r in rows)} dòng hợp lệ chưa gửi**')
        if sent==len(sending):st.success(f'Đã gửi thành công {sent}/{len(sending)} dòng trong lượt này.')
st.subheader('3. Xuất báo cáo')
st.download_button('Tải kết quả kiểm tra CSV',pd.DataFrame(summary).to_csv(index=False).encode('utf-8-sig'),file_name='kiem_tra_excel.csv',mime='text/csv')
st.caption('Hàng có trạng thái đang gửi/chưa xác minh không tự thử lại để tránh trùng. Nhật ký lưu trong output/submissions.sqlite3.')

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import openpyxl 
import sqlite3
from PIL import Image
import os
import base64

page_bg ="""
<style>
    .stApp{
        background-color: #fd9cb8;
    }
</style>        
"""
st.markdown(page_bg, unsafe_allow_html=True)

st.markdown("""
<style>
[data-testid-"stSidebar"]{
    background-color: #ffeaf1 !important;
}
</style>
""", unsafe_allow_html=True)

def export_to_excel():
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        export_list = {
            "df_data_transaksi": "Data Transaksi",
            "df_data_persediaan": "Data Persediaan",
            "df_data_beban": "Data Beban",
            "df_data_modal": "Data Modal",
            "df_neraca_saldo_periode_sebelumnya": "Neraca Saldo Periode Sebelumnya",
            "df_jurnal_umum": "Jurnal Umum",
            "df_buku_besar": "Buku Besar",
            "df_neraca_saldo": "Neraca Saldo",
            "df_laporan_laba_rugi": "Laporan Laba Rugi",
            "df_laporan_perubahan_modal": "Laporan Perubahan Modal",
            "df_laporan_posisi_keuangan": "Laporan Posisi Keuangan",
            "df_jurnal_penutup": "Jurnal Penutup",
            "df_neraca_saldo_setelah_penutup": "Neraca Saldo Setelah Penutup"
        }

        for key, sheet_name in export_list.items():
            if key in st.session_state and not st.session_state[key].empty:
                st.session_state[key].to_excel(writer, sheet_name=sheet_name, index=False)

        if "df_buku_besar" in st.session_state and not st.session_state.df_buku_besar.empty:
            df_buku_besar = st.session_state.df_buku_besar

            daftar_akun = [
                "kas", "persediaan", "perlengkapan", "aset biologis", "peralatan",
                "modal", "penjualan", "beban listrik dan air", "beban transportasi", "beban gaji"
            ]

            for akun in daftar_akun:
                df_akun = df_buku_besar[df_buku_besar["Nama Akun"].str.lower() == akun.lower()]
                if not df_akun.empty:
                    nama_sheet = akun[:31].replace('/', ' ').replace('\\', ' ').replace('*', ' ')\
                        .replace('[', ' ').replace(']', ' ').replace(':', ' ').replace('?', ' ')
                    df_akun.to_excel(writer, sheet_name=nama_sheet, index=False)

    buffer.seek(0)
    return buffer


def update_buku_besar():
    df_jurnal = st.session_state.get("df_jurnal_umum", pd.DataFrame())
    df_saldo_awal = st.session_state.get("df_neraca_saldo_periode_sebelumnya", 
pd.DataFrame())

    data = pd.concat([df_saldo_awal, df_jurnal], ignore_index=True)
    data["Debit (Rp)"] = data["Debit (Rp)"].fillna(0)
    data["Kredit (Rp)"] = data["Kredit (Rp)"].fillna(0)

    
    buku_besar = data.groupby("Nama Akun")[["Debit (Rp)", "Kredit (Rp)"]].sum().reset_index()
    buku_besar["Saldo (Rp)"] = buku_besar["Debit (Rp)"] - buku_besar["Kredit (Rp)"]

    st.session_state.df_buku_besar = buku_besar

    df_akun_template = pd.DataFrame({"Nama Akun": [
        "Kas", "Persediaan", "Perlengkapan", "Aset biologis", "Peralatan",
        "Penjualan", "Modal", "Beban listrik dan air", "Beban transportasi", "Beban gaji"]})

    neraca = df_akun_template.merge(buku_besar, on="Nama Akun", how="left").fillna(0)

    neraca_final = []
    for _, row in neraca.iterrows():
        debit = row["Debit (Rp)"] if row["Saldo (Rp)"] >= 0 else 0
        kredit = -row["Saldo (Rp)"] if row["Saldo (Rp)"] < 0 else 0
        neraca_final.append({"Nama Akun": row["Nama Akun"], "Debit (Rp)": debit, "Kredit (Rp)": kredit})

    df_neraca_saldo = pd.DataFrame(neraca_final)
    df_neraca_saldo.insert(0, "No", range(1, len(df_neraca_saldo)+1))

    total_debit = df_neraca_saldo["Debit (Rp)"].sum()
    total_kredit = df_neraca_saldo["Kredit (Rp)"].sum()
    total_row = {"No": "", "Nama Akun": "Total", "Debit (Rp)": total_debit, "Kredit (Rp)": total_kredit}
    df_neraca_saldo = pd.concat([df_neraca_saldo, pd.DataFrame([total_row])], ignore_index=True)

    st.session_state.df_neraca_saldo = df_neraca_saldo


def hitung_laba_rugi(df_jurnal):
    # ... (Fungsi hitung_laba_rugi tetap sama) ...
    kategori = {
        "Pendapatan": ["Penjualan"],
        "Beban": ["Beban listrik dan air", "Beban kendaraan", "Beban gaji", "Beban transportasi"] # Ditambahkan 'Beban transportasi'
    }

    df_jurnal = df_jurnal.copy()
    df_jurnal["Debit (Rp)"] = df_jurnal["Debit (Rp)"].fillna(0)
    df_jurnal["Kredit (Rp)"] = df_jurnal["Kredit (Rp)"].fillna(0)
    df_jurnal["Nama Akun"] = df_jurnal["Nama Akun"].astype(str)

    pendapatan = df_jurnal[df_jurnal["Nama Akun"].isin(kategori["Pendapatan"])]
    beban = df_jurnal[df_jurnal["Nama Akun"].isin(kategori["Beban"])]

    total_pendapatan = pendapatan["Kredit (Rp)"].sum()
    total_beban = beban["Debit (Rp)"].sum()
    laba_bersih = total_pendapatan - total_beban

    return total_pendapatan, total_beban, laba_bersih

def hitung_perubahan_modal(laba_bersih, modal_awal):
    # ... (Fungsi hitung_perubahan_modal tetap sama) ...
    perubahan_modal = {
        "Modal Awal 31 Maret": modal_awal,
        "Laba Bersih": laba_bersih,
        "Penambahan Modal": 0,
        "Modal Akhir 30 April": modal_awal + laba_bersih
    }
    return pd.DataFrame.from_dict(perubahan_modal, orient="index", columns=["Nilai (Rp)"])

def hitung_posisi_keuangan(df_buku_besar):
    # ... (Fungsi hitung_posisi_keuangan tetap sama) ...
    akun_aset_lancar = ["Kas", "Persediaan", "Perlengkapan"]
    akun_aset_tidak_lancar = ["Peralatan", "Aset biologis"]
    akun_liabilitas = ["Utang gaji", "Utang bank"]
    akun_ekuitas = ["Modal"]

    def total_akun(akun_list, kategori):
        # Ambil saldo terakhir untuk akun yang relevan
        df = df_buku_besar[df_buku_besar["Nama Akun"].isin(akun_list)].copy()
        
        # Di sini kita hanya mengambil saldo dari df_buku_besar (yang sudah summary)
        df_filtered = df[['Nama Akun', 'Saldo (Rp)']]
        df_filtered["Kategori"] = kategori
        return df_filtered

    aset_lancar = total_akun(akun_aset_lancar, "Aset Lancar")
    aset_tidak_lancar = total_akun(akun_aset_tidak_lancar, "Aset Tidak Lancar")
    
    # Liabilitas dan Ekuitas: Saldo diambil dari df_buku_besar, tetapi nilainya harus positif untuk laporan
    # (Asumsi saldo di df_buku_besar sudah Debit - Kredit)
    liabilitas = total_akun(akun_liabilitas, "Liabilitas")
    ekuitas = total_akun(akun_ekuitas, "Ekuitas")

    posisi = pd.concat([aset_lancar, aset_tidak_lancar, liabilitas, ekuitas], ignore_index=True)

    # Tambahkan total per kategori
    total_df = posisi.groupby("Kategori")["Saldo (Rp)"].sum().reset_index()
    total_df["Nama Akun"] = "Total " + total_df["Kategori"]
    posisi = pd.concat([posisi, total_df[["Nama Akun", "Saldo (Rp)", "Kategori"]]], ignore_index=True)

    # Tambahkan Total Aset dan Total Liabilitas + Ekuitas secara terpisah
    total_aset_value = total_df[total_df["Kategori"].isin(["Aset Lancar", "Aset Tidak Lancar"])]["Saldo (Rp)"].sum()
    total_liab_eq_value = total_df[total_df["Kategori"].isin(["Liabilitas", "Ekuitas"])]["Saldo (Rp)"].sum()

    total_rows = pd.DataFrame([
        {"Nama Akun": "Total Aset", "Saldo (Rp)": total_aset_value, "Kategori": "Ringkasan"},
        {"Nama Akun": "Total Liabilitas dan Ekuitas", "Saldo (Rp)": total_liab_eq_value, "Kategori": "Ringkasan"}
    ])

    posisi = pd.concat([posisi, total_rows], ignore_index=True)

    return posisi.drop(columns=["Kategori"]).fillna(0)

def create_connection():
    return sqlite3.connect("users.db", check_same_thread=False)

conn = create_connection()
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
""")
conn.commit()

def add_user(username, password):
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except:
        return False
def check_login(username, password):
    cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    return cur.fetchone()
def user_exists(username):
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cur.fetchone() is not None
def reset_password(username, new_pass):
    cur.execute("UPDATE users SET password = ? WHERE username = ?", (new_pass, username))
    conn.commit()


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

if "df_neraca_saldo_periode_sebelumnya" not in st.session_state:
    st.session_state.df_neraca_saldo_periode_sebelumnya = pd.DataFrame(columns=["No", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"])
if "df_jurnal_umum" not in st.session_state:
    st.session_state.df_jurnal_umum = pd.DataFrame(columns=["No", "Tanggal", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"])
if "df_buku_besar" not in st.session_state:
    st.session_state.df_buku_besar = pd.DataFrame(columns=["Nama Akun", "Debit (Rp)", "Kredit (Rp)", "Saldo (Rp)"])
if "df_neraca_saldo" not in st.session_state:
    st.session_state.df_neraca_saldo = pd.DataFrame(columns=["No", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"])
if "df_jurnal_penutup" not in st.session_state:
    st.session_state.df_jurnal_penutup = pd.DataFrame(columns=["No", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"])
if "df_neraca_saldo_setelah_penutup" not in st.session_state:
    st.session_state.df_neraca_saldo_setelah_penutup = pd.DataFrame(columns=["No", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"])

# --- Halaman Autentikasi ---
def auth_page():
    st.title("Selamat Datang")
    # ... (Isi fungsi auth_page tetap sama) ...
    tab_login, tab_register, tab_forgot = st.tabs(["Login", "Registrasi", "Lupa Password"])

    #LOGIN
    with tab_login:
        st.write("Halo! Silahkan login untuk mulai menggunakan aplikasi")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Selamat datang, {username}!")
                st.rerun() # Ganti st.stop() dengan st.rerun() untuk memuat ulang aplikasi
            else:
                st.error("❌ Username atau password salah.")

    #REGISTRASI
    with tab_register:
        st.write("Bergabung sekarang dan nikmati pengalaman pengelolaan laporan keuangan yang lebih cepat, aman, dan terorganisir.")
        new_user = st.text_input("Username Baru", key="reg_user")
        new_pass = st.text_input("Password Baru", type="password", key="reg_pass")
        confirm_pass = st.text_input("Konfirmasi Password", type="password", key="reg_confirm")

        if st.button("Daftar"):
            if new_user.strip() == "" or new_pass.strip() == "":
                st.warning("⚠ Username dan password tidak boleh kosong.")
            elif user_exists(new_user):
                st.error("❌ Username sudah terdaftar.")
            elif new_pass != confirm_pass:
                st.error("❌ Konfirmasi password tidak cocok.")
            else:
                if add_user(new_user, new_pass):
                    st.success("✅ Registrasi berhasil! Silakan login.")
                else:
                    st.error("Terjadi kesalahan saat registrasi.")

    #LUPA PASSWORD
    with tab_forgot:
        st.write("Jika lupa password, Anda dapat meresetnya di sini.")

        forgot_user = st.text_input("Masukkan Username", key="forgot_user")
        new_pass2 = st.text_input("Password Baru", type="password", key="forgot_new_pass")
        confirm_pass2 = st.text_input("Konfirmasi Password Baru", type="password", key="forgot_confirm_pass")

        if st.button("Reset Password"):
            if not user_exists(forgot_user):
                st.error("❌ Username tidak ditemukan.")
            elif new_pass2.strip() == "":
                st.error("❌ Password baru tidak boleh kosong.")
            elif new_pass2 != confirm_pass2:
                st.error("❌ Konfirmasi password tidak cocok.")
            else:
                reset_password(forgot_user, new_pass2)
                st.success("🔄 Password berhasil direset! Silakan login kembali.")

# --- TAMPILKAN HALAMAN AUTENTIKASI JIKA BELUM LOGIN ---
if not st.session_state.logged_in:
    auth_page()
    st.stop() # Hentikan eksekusi setelah menampilkan halaman auth


# Sidebar content
with st.sidebar:
    if st.session_state.username:
        st.markdown(f"👤 Login sebagai **{st.session_state.username}**")
    else:
        st.markdown("⚠️ Belum ada pengguna yang login.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None 
        st.success("Anda berhasil logout!")
        st.rerun() # Gunakan st.rerun() setelah logout untuk kembali ke halaman auth

    # NAVIGASI MENGGUNAKAN st.sidebar.radio
    st.sidebar.markdown("---") 
    selected = st.sidebar.radio("NIO FARM", 
                                [
                                    'Profile', 
                                    'Lokasi', 
                                    'Neraca Saldo Periode Sebelumnya', 
                                    'Jurnal Umum', 
                                    'Buku Besar', 
                                    'Neraca Saldo', 
                                    'Laporan Laba Rugi', 
                                    'Laporan Perubahan Modal', 
                                    'Laporan Posisi Keuangan', 
                                    'Jurnal Penutup', 
                                    'Neraca Saldo Setelah Penutup', 
                                    'Unduh Laporan Keuangan'
                                ], 
                                index=0 
                                )
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #ffeaf1 !important;
}

/* Hilangkan bullet bawaan radio */
div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

/* Styling teks menu */
div[role="radiogroup"] > label {
    display: flex !important;
    align-items: center;
    padding: 6px 8px;
    border-radius: 6px;
    cursor: pointer;
}

/* Tambahkan PANAH */
div[role="radiogroup"] > label::before {
    content: "🐐";
    font-size: 15px;
    color: white;
    margin-right: 8px;
    font-weight: 600;
}

/* Warna hover */
div[role="radiogroup"] > label:hover {
    background-color: #fd9cb8 !important;
}

/* ITEM TERPILIH */
div[role="radio"][aria-checked="true"] > label {
    background-color: #fd9cb8 !important;
    font-weight: 700 !important;
    color: white !important;
}

/* Panah ikut berubah saat terpilih */
div[role="radio"][aria-checked="true"] > label::before {
    color: white !important;
    content: "🐐";
}

/* Teks di dalam label */
[data-testid="stWidgetLabel"] {
    color: white !important;
}

</style>
""", unsafe_allow_html=True)

if selected == 'Profile':
    try:
        logo = Image.open("logo nio.jpg")
        buffered = BytesIO()
        logo.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        st.markdown(
            f"""
            <div style="
                display: flex; 
                justify-content: center; 
                align-items: center; 
                width: 100%;
                margin-bottom: -10px;">
                <img src="data:image/png;base64,{img_base64}" width="260">
            </div>
            <h1 style="
                text-align: center; 
                margin-top: 5px; 
                margin-bottom: 10px;">
                Nio Farm
            </h1>
            """,
            unsafe_allow_html=True
        )

    except FileNotFoundError:
        st.error("Logo tidak ditemukan. Pastikan file 'logo nio.jpg' ada di folder yang sama.")

    st.markdown("""
    <style>
    .profile-text {
        text-align: justify;
        max-width: 900px;
        margin: 0 auto;
        line-height: 1.7;
        font-size: 16px;
        opacity: 0;
        animation: fadeSlide 1.2s ease-out forwards;
    }
    @keyframes fadeSlide {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="profile-text">
    <p>Di balik setiap tetes kesegaran susu kambing Nio Farm, terdapat komitmen untuk menghadirkan kualitas terbaik dan pengalaman yang dapat dipercaya. Seiring berkembangangnya usaha, Nio Farm terus bertransformasi menjadi brand yang lebih modern, transparan, dan siap bersaing di industri peternakan lokal.</p>

    <p>Untuk menjaga konsistensi dalam operasional dan memastikan setiap keputusan bisnis diambil berdasarkan data yang akurat, Nio Farm menghadirkan sistem laporan keuangan yang terintegrasi. Dengan dukungan teknologi ini, Nio Farm tidak hanya menghasilkan susu kambing yang segar dan berkualitas, tetapi juga membangun fondasi bisnis yang kuat, profesional, dan berkelanjutan demi menghadirkan nilai terbaik bagi pelanggan, mitra, dan masa depan brand Nio Farm sendiri.</p>
    </div>
    """, unsafe_allow_html=True)

# Halaman Lokasi
elif selected == 'Lokasi':
    st.write(f"Anda sedang melihat data untuk **{selected}**.")
    st.write("""
        **Jl. Pamongan Sari No.90, Pedurungan Lor, Kec. Pedurungan,  
        Kota Semarang, Jawa Tengah 50192**
    """)
    # Perbaikan: Menggunakan komponen Google Maps embed yang diizinkan Streamlit
    map_embed = """
        <iframe 
            width="100%" 
            height="450" 
            style="border:0" 
            loading="lazy"
            allowfullscreen 
            referrerpolicy="no-referrer-when-downgrade"
            src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3960.312953256037!2d110.43577317376023!3d-6.971576468249673!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2e708b77a94a218d%3A0xc6657c9197c3697e!2sJl.%20Pamongan%20Sari%20No.90%2C%20Pedurungan%20Lor%2C%20Kec.%20Pedurungan%2C%20Kota%20Semarang%2C%20Jawa%20Tengah%2050192!5e0!3m2!1sid!2sid!4v1700676458514!5m2!1sid!2sid">
        </iframe>
    """ # Menggunakan embed map yang valid
    st.components.v1.html(map_embed, height=450)

# Halaman Neraca Saldo Periode Sebelumnya
elif selected == 'Neraca Saldo Periode Sebelumnya':
    st.subheader('Neraca Saldo Periode Sebelumnya 🧾')
    st.markdown('Periode 31 Maret 2025')

    # ... (Formulir dan logika Neraca Saldo Periode Sebelumnya tetap sama) ...
    with st.form("form_tambah_transaksi_neraca_saldo_periode_sebelumnya", clear_on_submit=True):
        nama_akun = st.selectbox("Nama Akun", ["Kas", "Persediaan", "Perlengkapan", "Aset biologis", "Peralatan", "Modal"])
        debit = st.number_input("Debit (Rp)", min_value=0, step=1000)
        kredit = st.number_input("Kredit (Rp)", min_value=0, step=1000)
        tambah = st.form_submit_button("Tambah Transaksi")

        if tambah:
            if debit == 0 and kredit == 0:
                st.warning("Isi salah satu nilai Debit atau Kredit.")
            else:
                nomor = len(st.session_state.df_neraca_saldo_periode_sebelumnya) + 1
                # Tambahkan kolom 'Tanggal' dan 'Keterangan' untuk konsistensi di Buku Besar/Jurnal
                row = {"No": nomor, "Tanggal": "31-03-2025", "Nama Akun": nama_akun, "Debit (Rp)": debit, "Kredit (Rp)": kredit, "Keterangan": "Saldo Awal"} 
                st.session_state.df_neraca_saldo_periode_sebelumnya = pd.concat([
                    st.session_state.df_neraca_saldo_periode_sebelumnya, pd.DataFrame([row])
                ], ignore_index=True)
                update_buku_besar()

        df = st.session_state.get("df_neraca_saldo_periode_sebelumnya", pd.DataFrame())
    st.markdown("### Edit Neraca Saldo Periode Sebelumnya")
    edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

    edited_df["Debit (Rp)"] = pd.to_numeric(edited_df["Debit (Rp)"], errors="coerce").fillna(0)
    edited_df["Kredit (Rp)"] = pd.to_numeric(edited_df["Kredit (Rp)"], errors="coerce").fillna(0)
    st.session_state.df_neraca_saldo_periode_sebelumnya = edited_df

    total_row = {
            "No": "",
            "Nama Akun": "Total",
            "Debit (Rp)": edited_df["Debit (Rp)"].sum(),
            "Kredit (Rp)": edited_df["Kredit (Rp)"].sum()
        }
    df_total = pd.concat([edited_df, pd.DataFrame([total_row])], ignore_index=True)
    st.markdown("### Jurnal Umum")
    st.dataframe(
            df_total.fillna(0).style.format({
                "Debit (Rp)": "Rp {:,.0f}",
                "Kredit (Rp)": "Rp {:,.0f}"
            }),
            use_container_width=True
        )

# Halaman Jurnal Umum
elif selected == "Jurnal Umum":
    st.subheader("Jurnal Umum 📓")
    st.markdown("Periode April 2025")

    # ... (Formulir dan logika Jurnal Umum tetap sama) ...
    with st.form("form_tambah_jurnal", clear_on_submit=True):
        tanggal = st.date_input("Tanggal")
        nama_akun = st.text_input("Nama Akun")
        debit = st.number_input("Debit (Rp)", min_value=0, step=1000)
        kredit = st.number_input("Kredit (Rp)", min_value=0, step=1000)
        tambah = st.form_submit_button("Tambah")

        if tambah:
            if nama_akun.strip() == "" or (debit == 0 and kredit == 0):
                st.warning("Nama akun wajib diisi dan salah satu nilai (debit/kredit) tidak boleh nol.")
            else:
                nomor = len(st.session_state.df_jurnal_umum) + 1
                row = {"No": nomor, "Tanggal": tanggal, "Nama Akun": nama_akun, "Debit (Rp)": debit, "Kredit (Rp)": kredit}
                st.session_state.df_jurnal_umum = pd.concat([
                    st.session_state.df_jurnal_umum, pd.DataFrame([row])
                ], ignore_index=True)
                update_buku_besar()

    df = st.session_state.get("df_jurnal_umum", pd.DataFrame())
    st.markdown("### Edit Jurnal Umum")
    edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

    edited_df["Debit (Rp)"] = pd.to_numeric(edited_df["Debit (Rp)"], errors="coerce").fillna(0)
    edited_df["Kredit (Rp)"] = pd.to_numeric(edited_df["Kredit (Rp)"], errors="coerce").fillna(0)
    st.session_state.df_jurnal_umum = edited_df

    total_row = {
            "No": "",
            "Nama Akun": "Total",
            "Debit (Rp)": edited_df["Debit (Rp)"].sum(),
            "Kredit (Rp)": edited_df["Kredit (Rp)"].sum()
        }
    df_total = pd.concat([edited_df, pd.DataFrame([total_row])], ignore_index=True)
    st.markdown("### Jurnal Umum")
    st.dataframe(
            df_total.fillna(0).style.format({
                "Debit (Rp)": "Rp {:,.0f}",
                "Kredit (Rp)": "Rp {:,.0f}"
            }),
            use_container_width=True
        )


# Halaman Buku Besar
elif selected == "Buku Besar":
    st.subheader("Buku Besar 📚")
    
    # PERBAIKAN: Panggil fungsi update_buku_besar untuk memastikan data terbaru
    update_buku_besar()

    df_buku_besar_summary = st.session_state.get("df_buku_besar", pd.DataFrame())
    df_jurnal = st.session_state.get("df_jurnal_umum", pd.DataFrame())
    df_saldo_awal = st.session_state.get("df_neraca_saldo_periode_sebelumnya", pd.DataFrame())
    
    # Gabungkan semua data transaksi (saldo awal dianggap transaksi)
    df_saldo_awal_transaksi = df_saldo_awal.rename(columns={"Debit (Rp)": "Debit", "Kredit (Rp)": "Kredit"})
    df_jurnal_transaksi = df_jurnal.rename(columns={"Debit (Rp)": "Debit", "Kredit (Rp)": "Kredit"})

    all_transactions = pd.concat([df_saldo_awal_transaksi, df_jurnal_transaksi], ignore_index=True)
    all_transactions["Tanggal"] = pd.to_datetime(all_transactions["Tanggal"], errors='coerce')
    all_transactions = all_transactions.sort_values(by=["Tanggal", "No"], na_position='first').fillna(0)
    
    semua_akun = df_buku_besar_summary["Nama Akun"].unique()

    if df_buku_besar_summary.empty:
        st.info("Buku Besar kosong. Tambahkan transaksi Neraca Saldo Periode Sebelumnya dan Jurnal Umum terlebih dahulu.")
    else:
        for akun in semua_akun:
            st.markdown(f"### Akun: {akun}")
            
            # Filter transaksi untuk akun ini
            transaksi_akun = all_transactions[all_transactions["Nama Akun"] == akun].copy()
            
            # Hitung saldo berjalan
            transaksi_akun["Saldo Kumulatif"] = (transaksi_akun["Debit"] - transaksi_akun["Kredit"]).cumsum()
            
            # Tampilkan hanya kolom yang relevan untuk buku besar
            df_display = transaksi_akun[["Tanggal", "Nama Akun", "Debit", "Kredit", "Saldo Kumulatif"]]
            df_display = df_display.rename(columns={"Debit": "Debit (Rp)", "Kredit": "Kredit (Rp)", "Saldo Kumulatif": "Saldo (Rp)"})
            
            # Dapatkan saldo akhir dari df_buku_besar_summary
            saldo_akhir = df_buku_besar_summary[df_buku_besar_summary["Nama Akun"] == akun]["Saldo (Rp)"].iloc[0]
            
            st.dataframe(
                df_display.style.format({
                    "Debit (Rp)": "Rp {:,.0f}",
                    "Kredit (Rp)": "Rp {:,.0f}",
                    "Saldo (Rp)": "Rp {:,.0f}"
                }),
                use_container_width=True
            )
            st.markdown(f"**Saldo Akhir {akun}: Rp {saldo_akhir:,.0f}**")


# Halaman Neraca Saldo
elif selected == "Neraca Saldo":
    st.subheader("Neraca Saldo 📋")
    update_buku_besar()
    df_neraca = st.session_state.get("df_neraca_saldo", pd.DataFrame())
    st.dataframe(df_neraca.style.format({
        "Debit (Rp)": "Rp {:,.0f}",
        "Kredit (Rp)": "Rp {:,.0f}"
    }), use_container_width=True)

# Halaman Laporan Laba Rugi
elif selected == "Laporan Laba Rugi":
    st.subheader("Laporan Laba Rugi 📊")
    df_jurnal = st.session_state.get("df_jurnal_umum", pd.DataFrame())
    pendapatan, beban, laba_bersih = hitung_laba_rugi(df_jurnal)
    st.metric("Total Pendapatan", f"Rp {pendapatan:,.0f}")
    st.metric("Total Beban", f"Rp {beban:,.0f}")
    st.metric("Laba Bersih", f"Rp {laba_bersih:,.0f}")

# Halaman Laporan Perubahan Modal
elif selected == "Laporan Perubahan Modal":
    st.subheader("Laporan Perubahan Modal 🔄")
    
    update_buku_besar() 
    
    df_jurnal = st.session_state.get("df_jurnal_umum", pd.DataFrame())
    df_buku_besar = st.session_state.get("df_buku_besar", pd.DataFrame())
    
    _, _, laba_bersih = hitung_laba_rugi(df_jurnal)
    
    # Ambil Modal Awal (dari Neraca Saldo Periode Sebelumnya)
    df_saldo_awal = st.session_state.get("df_neraca_saldo_periode_sebelumnya", pd.DataFrame())
    modal_awal = df_saldo_awal[df_saldo_awal["Nama Akun"].str.contains("Modal", case=False, na=False)]["Kredit (Rp)"].sum()
    
    df_modal = hitung_perubahan_modal(laba_bersih, modal_awal)
    st.dataframe(df_modal.style.format({"Nilai (Rp)": "Rp {:,.0f}"}), use_container_width=True)


# Halaman Laporan Posisi Keuangan
elif selected == "Laporan Posisi Keuangan":
    st.subheader("Laporan Posisi Keuangan 💰")
    update_buku_besar() 
    df_buku_besar = st.session_state.get("df_buku_besar", pd.DataFrame())
    df_posisi = hitung_posisi_keuangan(df_buku_besar)
    st.dataframe(df_posisi.style.format({"Saldo (Rp)": "Rp {:,.0f}"}), use_container_width=True)

# Halaman Jurnal Penutup
elif selected == 'Jurnal Penutup':
    st.subheader('Jurnal Penutup 🛑')
    st.markdown('Periode 30 April 2025')

    columns = ["No", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"]
    if "df_jurnal_penutup" not in st.session_state:
        st.session_state.df_jurnal_penutup = pd.DataFrame(columns=columns)

    with st.form("form_tambah_transaksi_jurnal_penutup", clear_on_submit=True):
        st.write("Tambah Transaksi")
        nama_akun = st.text_input("Nama Akun")
        debit = st.number_input("Debit (Rp)", min_value=0, step=1000)
        kredit = st.number_input("Kredit (Rp)", min_value=0, step=1000)
        col1, col2 = st.columns(2)

        with col1:
            tambah = st.form_submit_button("Tambah Transaksi")
        with col2:
            reset = st.form_submit_button("Reset Data")

        if tambah:
            if nama_akun.strip() == "" or (debit == 0 and kredit == 0):
                st.warning("Nama akun wajib diisi dan salah satu nilai (debit/kredit) tidak boleh nol.")
            else:
                nomor = len(st.session_state.df_jurnal_penutup) + 1
                row = {
                    "No": nomor,
                    "Nama Akun": nama_akun,
                    "Debit (Rp)": debit if debit > 0 else None,
                    "Kredit (Rp)": kredit if kredit > 0 else None
                }
                st.session_state.df_jurnal_penutup = pd.concat(
                    [st.session_state.df_jurnal_penutup, pd.DataFrame([row])],
                    ignore_index=True
                )
                st.success("Transaksi berhasil ditambahkan.")

        if reset:
            st.session_state.df_jurnal_penutup = pd.DataFrame(columns=columns)
            st.info("Data berhasil direset.")

    if st.session_state.df_jurnal_penutup.empty:
        st.info("Tabel belum memiliki transaksi. Tambahkan transaksi di atas.")
    else:
        df = st.session_state.df_jurnal_penutup.copy()
        # Logika edit dan total dipertahankan
        st.markdown("### Edit Jurnal Penutup")
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

        edited_df["Debit (Rp)"] = pd.to_numeric(edited_df["Debit (Rp)"], errors="coerce").fillna(0)
        edited_df["Kredit (Rp)"] = pd.to_numeric(edited_df["Kredit (Rp)"], errors="coerce").fillna(0)
        st.session_state.df_jurnal_penutup = edited_df

        total_row = {
            "No": "",
            "Nama Akun": "Total",
            "Debit (Rp)": edited_df["Debit (Rp)"].sum(),
            "Kredit (Rp)": edited_df["Kredit (Rp)"].sum()
        }
        df_total = pd.concat([edited_df, pd.DataFrame([total_row])], ignore_index=True)
        st.markdown("### Jurnal Penutup")
        st.dataframe(
            df_total.fillna(0).style.format({
                "Debit (Rp)": "Rp {:,.0f}",
                "Kredit (Rp)": "Rp {:,.0f}"
            }),
            use_container_width=True
        )


# Halaman Neraca Saldo Setelah Penutup
elif selected == 'Neraca Saldo Setelah Penutup':
    st.subheader('Neraca Saldo Setelah Penutup ✅') 
    st.markdown('Periode 30 April 2025')
    
    # ... (Logika Neraca Saldo Setelah Penutup tetap sama) ...
    columns = ["No", "Nama Akun", "Debit (Rp)", "Kredit (Rp)"]
    if "df_neraca_saldo_setelah_penutup" not in st.session_state:
        st.session_state.df_neraca_saldo_setelah_penutup = pd.DataFrame(columns=columns)

    with st.form("form_tambah_transaksi_setelah_penutup", clear_on_submit=True):
        st.write("Tambah Transaksi")
        nama_akun = st.text_input("Nama Akun")
        debit = st.number_input("Debit (Rp)", min_value=0, step=1000)
        kredit = st.number_input("Kredit (Rp)", min_value=0, step=1000)
        col1, col2 = st.columns(2)

        with col1:
            tambah = st.form_submit_button("Tambah Transaksi")
        with col2:
            reset = st.form_submit_button("Reset Data")

        if tambah:
            if nama_akun.strip() == "" or (debit == 0 and kredit == 0):
                st.warning("Nama akun wajib diisi dan salah satu nilai (debit/kredit) tidak boleh nol.")
            else:
                nomor = len(st.session_state.df_neraca_saldo_setelah_penutup) + 1
                row = {
                    "No": nomor,
                    "Nama Akun": nama_akun,
                    "Debit (Rp)": debit if debit > 0 else None,
                    "Kredit (Rp)": kredit if kredit > 0 else None
                }
                st.session_state.df_neraca_saldo_setelah_penutup = pd.concat(
                    [st.session_state.df_neraca_saldo_setelah_penutup, pd.DataFrame([row])],
                    ignore_index=True
                )
                st.success("Transaksi berhasil ditambahkan.")

        if reset:
            st.session_state.df_neraca_saldo_setelah_penutup = pd.DataFrame(columns=columns)
            st.info("Data berhasil direset.")

    if st.session_state.df_neraca_saldo_setelah_penutup.empty:
        st.info("Tabel belum memiliki transaksi. Tambahkan transaksi di atas.")
    else:
        df = st.session_state.df_neraca_saldo_setelah_penutup.copy()
        # Logika edit dan total dipertahankan
        st.markdown("### Edit Data Neraca Saldo Setelah Penutup")
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

        edited_df["Debit (Rp)"] = pd.to_numeric(edited_df["Debit (Rp)"], errors="coerce").fillna(0)
        edited_df["Kredit (Rp)"] = pd.to_numeric(edited_df["Kredit (Rp)"], errors="coerce").fillna(0)
        st.session_state.df_neraca_saldo_setelah_penutup = edited_df

        total_row = {
            "No": "",
            "Nama Akun": "Total",
            "Debit (Rp)": edited_df["Debit (Rp)"].sum(),
            "Kredit (Rp)": edited_df["Kredit (Rp)"].sum()
        }
        df_total = pd.concat([edited_df, pd.DataFrame([total_row])], ignore_index=True)

        st.markdown("### Neraca Saldo Setelah Penutup (dengan Total)")
        st.dataframe(
            df_total.fillna(0).style.format({
                "Debit (Rp)": "Rp {:,.0f}",
                "Kredit (Rp)": "Rp {:,.0f}"
            }),
            use_container_width=True
        )

# Halaman Unduh Laporan Keuangan
elif selected == 'Unduh Laporan Keuangan':
    st.subheader('Unduh Laporan Keuangan') 
    st.markdown("Pada halaman ini, Anda dapat mengunduh laporan keuangan dalam bentuk file Excel.")

    try:
        import xlsxwriter
        st.success("Modul berhasil diimpor!")
        buffer = export_to_excel()

        # Tombol unduh
        st.download_button(
            label="📥 Unduh Semua Data Laporan (Excel)",
            data=buffer,
            file_name="laporan_keuangan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except ModuleNotFoundError:
        st.error("Modul xlsxwriter tidak ditemukan. Silakan instal dengan menjalankan: pip install xlsxwriter")
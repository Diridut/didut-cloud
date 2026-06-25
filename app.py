import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from dotenv import load_dotenv

# Membaca konfigurasi variabel dari file .env
load_dotenv()

app = Flask(__name__)
# Secret key wajib aktif untuk mengamankan data session/login di browser
app.secret_key = "siakad_secret_key_didut_2026"

# Menghubungkan ke database cloud Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# ==========================================
# 0. ROUTE FITUR LOGIN, REGISTER & LOGOUT
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_input = request.form.get('username')
        password_input = request.form.get('password')
        
        try:
            # Mencari data kecocokan akun di tabel 'pengguna' Supabase Cloud
            response = supabase.table('pengguna')\
                .select('*')\
                .eq('username', username_input)\
                .eq('password', password_input)\
                .execute()
            
            # Jika data akun ditemukan di cloud, simpan status login ke session
            if response.data:
                user_data = response.data[0]
                session['logged_in'] = True
                session['role'] = user_data['role']
                session['username'] = user_data['username'].capitalize()
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Username atau Password salah!")
                
        except Exception as e:
            print(f"Error login cloud: {e}")
            return render_template('login.html', error="Gagal terhubung ke server auth cloud.")
            
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username_input = request.form.get('username').lower().strip()
    password_input = request.form.get('password')
    role_input = request.form.get('role')
    
    try:
        # 1. Cek dulu apakah username sudah terpakai di cloud
        cek_user = supabase.table('pengguna').select('*').eq('username', username_input).execute()
        if cek_user.data:
            return render_template('login.html', error="Username tersebut sudah terdaftar! Gunakan nama lain.")
        
        # 2. Jika aman, langsung insert/simpan ke tabel pengguna di Supabase Cloud
        supabase.table('pengguna').insert({
            "username": username_input,
            "password": password_input,
            "role": role_input
        }).execute()
        
        return render_template('login.html', success="Akun berhasil dibuat di Cloud! Silakan masuk di tab 'Masuk'.")
        
    except Exception as e:
        print(f"Error registrasi: {e}")
        return render_template('login.html', error="Gagal menyimpan akun baru ke database cloud.")

@app.route('/logout')
def logout():
    # Menghapus semua data session login
    session.clear()
    return redirect(url_for('login'))


# ==========================================
# 1. ROUTE HALAMAN UTAMA (DASHBOARD)
# ==========================================
@app.route('/')
def home():
    # Pelindung: Jika belum login, tendang balik ke halaman login
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        # Mengambil total data real-time dari cloud untuk statistik dashboard
        res_mhs = supabase.table('mahasiswa').select('id').execute()
        res_mk = supabase.table('mata_kuliah').select('id').execute()
        
        total_mhs = len(res_mhs.data) if res_mhs.data else 0
        total_mk = len(res_mk.data) if res_mk.data else 0
    except Exception as e:
        print(f"Error stats dashboard: {e}")
        total_mhs, total_mk = 0, 0
        
    return render_template('index.html', total_mahasiswa=total_mhs, total_matakuliah=total_mk, user=session)


# ==========================================
# 2. ROUTE MANAJEMEN DATA MAHASISWA
# ==========================================
@app.route('/mahasiswa')
def lihat_mahasiswa():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        response = supabase.table('mahasiswa').select('*').execute()
        daftar_mhs = response.data if response.data else []
    except Exception as e:
        print(f"Error fetch mahasiswa: {e}")
        daftar_mhs = []
    return render_template('mahasiswa.html', mahasiswa_list=daftar_mhs, user=session)

@app.route('/tambah-mahasiswa', methods=['POST'])
def tambah_mahasiswa():
    # Proteksi hak akses: Hanya role dosen yang boleh menambahkan data ke cloud
    if session.get('role') != 'dosen':
        return "Akses Ditolak! Hanya akun dosen yang diizinkan menambah data.", 403
        
    nim = request.form.get('nim')
    nama = request.form.get('nama')
    jurusan = request.form.get('jurusan')
    try:
        supabase.table('mahasiswa').insert({"nim": nim, "nama": nama, "jurusan": jurusan}).execute()
    except Exception as e:
        print(f"Gagal menyimpan mhs ke cloud: {e}")
    return redirect(url_for('lihat_mahasiswa'))


# ==========================================
# 3. ROUTE MANAJEMEN MATA KULIAH
# ==========================================
@app.route('/matakuliah')
def lihat_matakuliah():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        response = supabase.table('mata_kuliah').select('*').execute()
        daftar_mk = response.data if response.data else []
    except Exception as e:
        print(f"Error fetch matkul: {e}")
        daftar_mk = []
    return render_template('matakuliah.html', matakuliah_list=daftar_mk, user=session)

@app.route('/tambah-matakuliah', methods=['POST'])
def tambah_matakuliah():
    if session.get('role') != 'dosen':
        return "Akses Ditolak! Hanya akun dosen yang diizinkan menambah data.", 403
        
    kode_matkul = request.form.get('kode_matkul')
    nama_matkul = request.form.get('nama_matkul')
    sks = request.form.get('sks')
    try:
        supabase.table('mata_kuliah').insert({"kode_matkul": kode_matkul, "nama_matkul": nama_matkul, "sks": int(sks)}).execute()
    except Exception as e:
        print(f"Gagal menyimpan matkul ke cloud: {e}")
    return redirect(url_for('lihat_matakuliah'))


# ==========================================
# 4. ROUTE MANAJEMEN NILAI AKADEMIK
# ==========================================
@app.route('/nilai')
def lihat_nilai():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    try:
        # Mengambil daftar nilai serta data mahasiswa dan matkul untuk opsi dropdown form
        res_nilai = supabase.table('nilai').select('*').execute()
        res_mhs = supabase.table('mahasiswa').select('nim', 'nama').execute()
        res_mk = supabase.table('mata_kuliah').select('kode_matkul', 'nama_matkul').execute()
        
        daftar_nilai = res_nilai.data if res_nilai.data else []
        daftar_mhs = res_mhs.data if res_mhs.data else []
        daftar_mk = res_mk.data if res_mk.data else []
    except Exception as e:
        print(f"Error fetch nilai: {e}")
        daftar_nilai, daftar_mhs, daftar_mk = [], [], []
        
    return render_template('nilai.html', nilai_list=daftar_nilai, mahasiswa_list=daftar_mhs, matakuliah_list=daftar_mk, user=session)

@app.route('/tambah-nilai', methods=['POST'])
def tambah_nilai():
    if session.get('role') != 'dosen':
        return "Akses Ditolak! Hanya akun dosen yang diizinkan menginput nilai.", 403
        
    nim_mahasiswa = request.form.get('nim_mahasiswa')
    kode_matkul = request.form.get('kode_matkul')
    angka_nilai = int(request.form.get('angka_nilai'))
    
    # Aturan otomatisasi konversi nilai angka ke huruf mutu akademik
    if angka_nilai >= 80: huruf_nilai = 'A'
    elif angka_nilai >= 70: huruf_nilai = 'B'
    elif angka_nilai >= 60: huruf_nilai = 'C'
    elif angka_nilai >= 50: huruf_nilai = 'D'
    else: huruf_nilai = 'E'
        
    try:
        supabase.table('nilai').insert({
            "nim_mahasiswa": nim_mahasiswa, 
            "kode_matkul": kode_matkul,
            "angka_nilai": angka_nilai, 
            "huruf_nilai": huruf_nilai
        }).execute()
    except Exception as e:
        print(f"Gagal menyimpan data nilai ke cloud: {e}")
        
    return redirect(url_for('lihat_nilai'))


if __name__ == '__main__':
    # Menjalankan server Flask lokal dengan debug mode aktif
    app.run(debug=True)
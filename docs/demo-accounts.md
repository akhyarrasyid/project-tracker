# Demo Accounts

Profile `release_demo` menyediakan akun berikut:

| Username | Peran | Kegunaan Demo |
|---|---|---|
| `admin` | Global Admin | Mengakses seluruh project dan fitur administrasi |
| `payment_owner` | Project Owner | Mengelola Payment Platform dan flow project owner |
| `engineering_member` | Member | Mengerjakan issue, comment, watcher, dan Inbox |
| `legal_member` | Legal/Compliance Member | Menguji project lintas fungsi dan permission |
| `viewer_user` | Viewer | Menguji akses read-only dan larangan mutasi |

Password tidak disimpan di Git.

Password akun demo berasal dari environment variable:

```text
DEMO_SEED_PASSWORD
```

Semua akun demo menggunakan shared password yang sama ketika profile `release_demo` dijalankan.

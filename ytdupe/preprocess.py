import logging
import re
import string

from tqdm import tqdm

logger = logging.getLogger("ytdupe")

STOPWORDS_ID = frozenset(
    {
        "ada", "adalah", "adapun", "agar", "akan", "akhir",
        "akhirnya", "aku", "akulah", "alhasil", "allah", "antara",
        "antaranya", "apa", "apabila", "apakah", "apalagi", "artinya",
        "asal", "atas", "atau", "ataupun", "awal", "bagai", "bagaimana",
        "bagaimanapun", "bagi", "bagian", "bahkan", "bahwa", "baik",
        "baiklah", "banyak", "baru", "bawah", "beberapa", "begitu",
        "begitupun", "beberapa", "belakangan", "belum", "belumlah",
        "benar", "benar-benar", "berarti", "berawal", "berbagai",
        "berdatangan", "beri", "berikan", "berikut", "berjumlah",
        "berkata", "berkenaan", "berlainan", "berlalu", "berlangsung",
        "berlebihan", "bermacam", "bermaksud", "bermula", "bersama",
        "bersiap", "bertanya", "berturut", "berupa", "betul", "biasa",
        "biasanya", "bila", "bilakah", "bilamana", "bisa", "biar",
        "biarpun", "bila", "bilamana", "bisa", "biar", "biarpun",
        "bingung", "boleh", "bolehkah", "buat", "bukan", "bukanlah",
        "bukannya", "bulan", "bung", "cara", "caranya", "cukup",
        "cukupkah", "cuma", "dahulu", "dalam", "dan", "dapat", "dari",
        "daripada", "datang", "deh", "demikian", "dengan", "depan",
        "di", "dia", "diakhiri", "diakhirinya", "dialah", "diantara",
        "diantaranya", "diberi", "diberikan", "diberikannya", "dibuat",
        "dibuatnya", "didapat", "didatangkan", "digunakan", "diibaratkan",
        "diibaratkannya", "diingat", "diingatkan", "diinginkan", "dijawab",
        "dijelaskan", "dilakukan", "dilalui", "dilihat", "dimaksud",
        "dimaksudkan", "dimaksudkannya", "dimaksudnya", "diminta",
        "dimisalkan", "dimulai", "dimulailah", "dimulainya", "dimungkinkan",
        "dini", "dipastikan", "diperbuat", "diperbuatnya", "dipergunakan",
        "diperkirakan", "diperlukan", "dipersoalkan", "dipertanyakan",
        "dipunyai", "diri", "dirinya", "disampaikan", "disebut", "disebutkan",
        "disebutkannya", "disini", "disinilah", "ditambahkan", "ditandaskan",
        "ditanya", "ditanyai", "ditanyakan", "ditegaskan", "ditujukan",
        "ditunjuk", "ditunjuki", "ditunjukkan", "ditunjukkannya", "ditunjuknya",
        "dituturkan", "dituturkannya", "diucapkan", "diucapkannya",
        "diungkapkan", "dong", "dua", "dulu", "empat", "engkau", "engkaulah",
        "enggak", "enggaknya", "entah", "entahlah", "gua", "gue", "gw",
        "hal", "hampir", "hanya", "hanyalah", "hari", "harus", "haruslah",
        "harusnya", "hendak", "hendaklah", "hendaknya", "hingga", "ia",
        "ialah", "ibaratkan", "ibaratnya", "ibu", "ikut", "ingat",
        "ingin", "inginkah", "inginkan", "ini", "inikah", "inilah",
        "itu", "itukah", "itulah", "jadi", "jadilah", "jadinya", "jangan",
        "jangankan", "janganlah", "jauh", "jawab", "jawaban", "jawabnya",
        "jelas", "jelaskan", "jelaslah", "jelasnya", "jika", "jikalau",
        "juga", "jumlah", "jumlahnya", "justru", "kala", "kalau", "kalaulah",
        "kalaupun", "kalian", "kami", "kamilah", "kamu", "kamulah", "kan",
        "kapan", "kapankah", "kapanpun", "karena", "karenanya", "kasus",
        "kata", "katakan", "katakanlah", "katanya", "ke", "keadaan",
        "kebetulan", "kecil", "kedua", "keduanya", "keinginan", "kelamaan",
        "kelihatan", "kelihatannya", "kelima", "keluar", "kembali",
        "kemudian", "kemungkinan", "kemungkinannya", "kenapa", "kepada",
        "kepadanya", "kesampaian", "keseluruhan", "keseluruhannya",
        "keterangan", "ketika", "khususnya", "kini", "kinilah", "kira",
        "kiranya", "kita", "kitalah", "kok", "kurang", "lagi", "lagian",
        "lah", "lain", "lainnya", "lalu", "lama", "lamanya", "langsung",
        "lanjut", "lanjutnya", "lebih", "lebihnya", "lu", "lalu", "lakukan",
        "lakukannya", "lalui", "lama", "langsung", "lebih", "lewat",
        "lima", "lu", "lumayan", "lungo", "maha", "mau", "maupun",
        "macam", "maka", "makanya", "makin", "malah", "malahan", "mungkin",
        "mungkinlah", "masa", "masalah", "masalahnya", "masih", "masihkah",
        "masing", "mau", "melainkan", "melakukan", "melalui", "melihat",
        "melihatnya", "memang", "memastikan", "memberi", "memberikan",
        "membuat", "memiliki", "meminta", "memintanya", "memisalkan",
        "memperbuat", "mempergunakan", "memperkirakan", "memperlihatkan",
        "mempersiapkan", "mempersoalkan", "mempertanyakan", "mempunyai",
        "memulai", "memungkinkan", "menaiki", "menambahkan", "menandaskan",
        "menanti", "menantikan", "menanya", "menanyai", "menanyakan",
        "mendapat", "mendapatkan", "mendatang", "mendatangi", "mendatangkan",
        "menegaskan", "mengakhiri", "mengapa", "mengatakan", "mengatakannya",
        "mengenai", "mengerjakan", "menggambarkan", "mengibaratkan",
        "mengibaratkannya", "mengingat", "mengingatkan", "menginginkan",
        "mengira", "mengucapkan", "mengucapkannya", "mengungkapkan",
        "menjadi", "menjawab", "menjelaskan", "menuju", "menunjuk",
        "menunjuki", "menunjukkan", "menunjuknya", "menurut", "menuturkan",
        "menuturkannya", "menyampaikan", "menyangkut", "menyatakan",
        "menyebutkan", "menyeluruh", "menyiapkan", "merasa", "mereka",
        "merekalah", "merupakan", "meski", "meskipun", "meyakini", "meyakinkan",
        "minta", "mirip", "misal", "misalkan", "misalnya", "mu", "mula",
        "mulai", "mulailah", "mulanya", "mungkin", "nah", "naik", "namun",
        "nanti", "nantinya", "nya", "nyaris", "nyatanya", "oleh", "olehnya",
        "pada", "padahal", "padanya", "pak", "paling", "panjang", "pantas",
        "para", "pasti", "pastilah", "penting", "pentingnya", "per",
        "percuma", "perlu", "perlukah", "perlunya", "pernah", "persoalan",
        "pertanyaan", "pertanyakan", "pihak", "pihaknya", "pukul", "pula",
        "pun", "punya", "rasa", "rasanya", "rata", "rupanya", "saat",
        "saatnya", "saja", "sajalah", "saling", "sama", "sampai", "sampaikan",
        "sana", "sangat", "sangatlah", "satu", "saya", "sayalah", "se",
        "sebab", "sebabnya", "sebagai", "sebagaimana", "sebagainya",
        "sebagian", "sebaik", "sebaiknya", "sebaliknya", "sebanyak",
        "sebegini", "sebegitu", "sebelum", "sebelumnya", "sebenarnya",
        "seberapa", "sebesar", "sebetulnya", "sebisanya", "sebuah", "sebuth",
        "sebab", "secukupnya", "sedang", "sedangkan", "sedemikian", "sedikit",
        "sedikitnya", "seenaknya", "segala", "segalanya", "segera",
        "seharusnya", "sehingga", "seingat", "sejak", "sejauh", "sejenak",
        "sejumlah", "sekadar", "sekadarnya", "sekali", "sekalian", "sekaligus",
        "sekalipun", "sekarang", "sekecil", "seketika", "sekiranya",
        "sekitar", "sekitarnya", "sekurang", "sekurangnya", "sela", "selain",
        "selaku", "selalu", "selama", "selamanya", "seluruh", "seluruhnya",
        "semacam", "semakin", "semampu", "semampunya", "semasa", "semasih",
        "semata", "semata-mata", "semau", "sementara", "semisal", "semisalnya",
        "sempat", "semua", "semuanya", "semula", "sendiri", "sendirian",
        "sendirinya", "seolah", "seorang", "sepanjang", "sepantasnya",
        "sepantasnyalah", "seperlunya", "seperti", "sepertinya", "sepihak",
        "sering", "seringnya", "serta", "serupa", "sesaat", "sesama",
        "sesampai", "sesegera", "sesekali", "seseorang", "sesuatu",
        "sesuatunya", "sesudah", "sesudahnya", "setelah", "setengah",
        "seterusnya", "setiap", "setiba", "setidaknya", "setinggi",
        "seusai", "sewaktu", "siap", "siapa", "siapakah", "siapapun",
        "sini", "sinilah", "sih", "soal", "soalnya", "suatu", "sudah",
        "sudahkah", "sudahlah", "supaya", "tadi", "tadinya", "tahu",
        "tahun", "tak", "tapi", "taruh", "telah", "tempat", "tengah",
        "tentang", "tentu", "tentulah", "tentunya", "tepat", "terakhir",
        "terasa", "terbanyak", "terdahulu", "terdapat", "terdiri", "terhadap",
        "terhadapnya", "teringat", "terjadi", "terjadilah", "terjadinya",
        "terjelma", "terkira", "terlalu", "terlebih", "terlihat", "termasuk",
        "ternyata", "tersampaikan", "tersebut", "tersebutlah", "tertentu",
        "tertuju", "terus", "terutama", "tetap", "tetapi", "tiap", "tiba",
        "tidak", "tidakkah", "tidaklah", "tiga", "toh", "tunjuk", "turut",
        "tutur", "tuturnya", "ucap", "ucapnya", "ujar", "ujarnya", "umum",
        "umumnya", "ungkap", "ungkapnya", "untuk", "usah", "usai", "waktu",
        "waktunya", "walau", "walaupun", "wong", "yaitu", "yakin", "yakni",
        "yang",
    }
)


_stemmer_instance = None


def _get_stemmer():
    global _stemmer_instance
    if _stemmer_instance is not None:
        return _stemmer_instance
    try:
        from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

        factory = StemmerFactory()
        _stemmer_instance = factory.createStemmer()
        return _stemmer_instance
    except ImportError:
        logger.warning("Sastrawi tidak tersedia. Stemming dilewati.")
        return None


def normalize(text: str, use_stemming: bool = False) -> str:
    if not text:
        return ""

    text = text.lower()

    text = text.translate(str.maketrans("", "", string.punctuation))

    text = re.sub(r"\b\d+\b", "", text)

    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    words = [w for w in words if w not in STOPWORDS_ID and len(w) > 1]

    if use_stemming and words:
        stemmer = _get_stemmer()
        if stemmer:
            words = [stemmer.stem(w) for w in words]

    return " ".join(words)


def normalize_transcripts(
    transcripts: dict[str, str], use_stemming: bool = False
) -> dict[str, str]:
    result: dict[str, str] = {}
    items = list(transcripts.items())

    for video_id, text in tqdm(items, desc="Preprocessing transkrip", unit="video"):
        normalized = normalize(text, use_stemming)
        if normalized.strip():
            result[video_id] = normalized

    logger.info(
        "Preprocessing selesai: %d dari %d transkrip berhasil",
        len(result),
        len(items),
    )
    return result

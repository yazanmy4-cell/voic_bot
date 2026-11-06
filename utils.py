import random
import json
import time


def user_agent():
    versions = ['4.0.18P6','4.0.19P7','4.0.20P1','4.1.0P3','4.1.5P2','4.2.1P8',
                '4.2.3P1','5.0.1B2','5.0.2P4','5.1.0P1','5.2.0B1','5.2.5P3',
                '5.3.0B1','5.3.2P2','5.4.0P1','5.4.3B2','5.5.0P1','5.5.2P3']
    models = ['SM-A125F','SM-A225F','SM-A325M','SM-A515F','SM-A725F','SM-M215F','SM-M325FV',
              'Redmi 9A','Redmi 9C','POCO M3','POCO M4 Pro','RMX2185','RMX3085',
              'moto g(9) play','CPH2239','V2027','OnePlus Nord','ASUS_Z01QD']
    android_versions = ['9','10','11','12','13','14']
    languages = ['en-US','es-MX','pt-BR','id-ID','ru-RU','hi-IN']
    countries = ['USA','ME','BRA','IDN','RUS','IND']
    return f"GarenaMSDK/{random.choice(versions)}({random.choice(models)};Android {random.choice(android_versions)};{random.choice(languages)};{random.choice(countries)};)"


def oauth_headers():
    return {
        'User-Agent': user_agent(),
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB54",
    }


def default_headers(ob_version="OB55"):
    return {
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "X-Ga-Sv": str(int(time.time())),
        "Authorization": "Bearer ",
        "X-Ga": "v1 1",
        "Releaseversion": ob_version,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
    }


def log(tag, message):
    print(f"{tag} = > {message}")


def load_accounts(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict):
                        result.append((str(item["uid"]), str(item["password"])))
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        result.append((str(item[0]), str(item[1])))
                return result
            elif isinstance(data, dict):
                return [(str(k), str(v)) for k, v in data.items()]
            return []
    except Exception as e:
        log("ERROR", f"Failed to load accounts from {filepath} => {e}")
        return []
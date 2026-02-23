import hashlib
import re
import bcrypt

def verify_bcrypt(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    # 去掉前缀
    hashed = hashed_password.replace("$bcrypt$", "")
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)



def verify_argon2(plain_password: str, hashed_password: str) -> bool:
    """验证 argon2 哈希"""
    try:
        import argon2
        ph = argon2.PasswordHasher()
        # 去掉前缀
        hash_str = hashed_password.replace("$argon2$", "")
        ph.verify(hash_str, plain_password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False
    except Exception:
        return False


def get_hash_password(password: str, algorithm="bcrypt"):
    password_bytes = password.encode('utf-8')

    if algorithm == "bcrypt":
        # bcrypt 自动生成盐值，工作因子12（可调整）
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return f"$bcrypt${hashed.decode('utf-8')}"

    elif algorithm == "argon2":
        import argon2
        ph = argon2.PasswordHasher(
            time_cost=2,  # 迭代次数
            memory_cost=65536,  # 内存消耗 (64MB)
            parallelism=4,  # 并行度
            hash_len=32,
            salt_len=16
        )
        hashed = ph.hash(password)
        return f"$argon2${hashed}"

    return None


def verify_password(plain_password, hashed_password):

    if not plain_password or not hashed_password:
        return False

    if hashed_password.startswith("$bcrypt$"):
        return verify_bcrypt(plain_password, hashed_password)
    elif hashed_password.startswith("$argon2$"):
        return verify_argon2(plain_password, hashed_password)
    else:
        return False

def check_password_complexity(password: str, min_length: int = 8,
                              require_letter: bool = True,
                              require_digit: bool = True,
                              require_upper: bool = False,
                              require_lower: bool = False,
                              require_special: bool = False) -> tuple[bool, str]:

    if len(password) < min_length:
        return False, f"密码长度不能少于{min_length}位"

    if require_letter and not re.search(r'[a-zA-Z]', password):
        return False, "密码必须包含至少一个字母"

    if require_digit and not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"

    if require_upper and not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"

    if require_lower and not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"

    if require_special and not re.search(r'[^a-zA-Z0-9]', password):
        return False, "密码必须包含至少一个特殊字符"

    return True, "密码复杂度符合要求"

def check_valid_email(email: str) -> bool:
    if not isinstance(email, str):
        return False

    # 基本格式正则：本地部分 + @ + 域名部分
    # 本地部分：字母数字._%+-（至少一个字符）
    # 域名部分：字母数字.-（至少一个点分隔，顶级域名至少两个字母）
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False

    # 分离本地部分和域名
    try:
        local, domain = email.rsplit('@', 1)
    except ValueError:
        return False  # 没有 @

    # 检查域名不能以点开头或结尾，不能有连续的点
    if domain.startswith('.') or domain.endswith('.'):
        return False
    if '..' in domain:
        return False

    # 检查域名标签是否合法（每个标签不能以减号开头或结尾）
    labels = domain.split('.')
    for label in labels:
        if not label:  # 空标签（例如连续的点已排除）
            return False
        if label.startswith('-') or label.endswith('-'):
            return False
        # 标签只能包含字母数字和减号（已在正则中基本保证，但减号首尾已检查）

    # 可选：检查顶级域名长度（已在正则中保证至少2个字母）
    return True
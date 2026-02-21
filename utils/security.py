import re
from passlib.context import CryptContext

# 创建密码上下文
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


# 密码加密
def get_hash_password(password: str):
    return pwd_context.hash(password)


# 密码验证: verify 返回值是布尔型
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def check_password_complexity(password: str, min_length: int = 6,
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
import hashlib
import itertools
import string

special_characters = string.punctuation
target_hash = "d8dd241199d2617765d7613fdd1df5358297b55f258647fe463de586bbfe3ebf"

combinations = itertools.product(special_characters, repeat=3)

for item in combinations:
    special_chars = ''.join(item)
    password = f"GR{special_chars}sunshinectf8_"
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash == target_hash:
        print(f"Password: {password}")
        break
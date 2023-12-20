from cryptography.fernet import Fernet

def generate_key():
    """
    Generates a key and save it into a file
    """
    key = Fernet.generate_key()
    print(" =======> secret.key <=========")
    print("COPY IT TO SECURE PLACE")
    with open("secret.key", "wb") as key_file:
        key_file.write(key)

generate_key()

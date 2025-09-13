import hashlib
import uuid


class HashFunction:
    """
    Helper class for hashing data.

    Methods:
        get_hash(): Compute and return the hash of the input data as a hexadecimal string.
    """

    def __init__(self, algorithm: str = "uuid5"):
        """
        Initialize the hash function with the specified algorithm.

        Supported algorithms: md5, sha1, sha256, uuid5
        """
        self.algorithm: str = algorithm.lower()
        if (
            self.algorithm not in hashlib.algorithms_guaranteed
            and self.algorithm != "uuid5"
        ):
            raise ValueError(f"Unsupported hash algorithm: {self.algorithm}")

    def get_hash(self, data: str) -> uuid.UUID:
        """Compute and return the hash of the input data as a hexadecimal string. Output is truncated to 32 characters."""
        if self.algorithm == "uuid5":
            return uuid.uuid5(uuid.NAMESPACE_URL, data)
        else:
            raise NotImplementedError("Unsupported hash algorithm")

import ctypes
import os
import threading

import numpy as np


class CDetectedFace(ctypes.Structure):
    _fields_ = [
        ("top", ctypes.c_int),
        ("right", ctypes.c_int),
        ("bottom", ctypes.c_int),
        ("left", ctypes.c_int),
        ("confidence", ctypes.c_float),
        ("embedding", ctypes.c_float * 128),
    ]


class CInferenceResult(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_int),
        ("error_code", ctypes.c_int),
        ("faces", ctypes.POINTER(CDetectedFace)),
    ]


class CFaceEngine:
    def __init__(self, lib_path: str = "/app/c_engine/libfacereco.so"):
        # Support for launch in Docker and in local testing
        if not os.path.exists(lib_path):
            fallback = os.path.join(os.path.dirname(__file__), "c_engine", "libfacereco.so")
            if os.path.exists(fallback):
                lib_path = fallback
            else:
                raise FileNotFoundError(f"Cannot find shared library at {lib_path}")

        self._lib = ctypes.CDLL(lib_path)
        self._lock = threading.Lock()

        # Configure C function signatures
        self._lib.init_engine.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        self._lib.init_engine.restype = ctypes.c_int

        self._lib.process_image_memory.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_int,
            ctypes.c_float,
            ctypes.c_float,
        ]
        self._lib.process_image_memory.restype = CInferenceResult

        self._lib.free_inference_result.argtypes = [ctypes.POINTER(CInferenceResult)]
        self._lib.free_inference_result.restype = None

        self._lib.cleanup_engine.argtypes = []
        self._lib.cleanup_engine.restype = None

    def initialize(
        self,
        models_dir: str = "/app/c_engine/models",
        num_threads: int = 0,
    ) -> None:
        if not os.path.exists(models_dir):
            models_dir = os.path.join(os.path.dirname(__file__), "c_engine", "models")

        yunet_cfg = os.path.join(models_dir, "yunet.cfg").encode("utf-8")
        yunet_weights = os.path.join(models_dir, "yunet_weights").encode("utf-8")
        sface_cfg = os.path.join(models_dir, "sface.cfg").encode("utf-8")
        sface_weights = os.path.join(models_dir, "sface_weights").encode("utf-8")

        status = self._lib.init_engine(
            yunet_cfg, yunet_weights, sface_cfg, sface_weights, num_threads
        )
        if status != 0:
            raise RuntimeError(f"Engine initialization failed with code {status}")

    def detect_and_encode(
        self, image_bytes: bytes, score_thresh: float = 0.6, nms_thresh: float = 0.3
    ) -> list[dict]:
        if not image_bytes:
            raise ValueError("Empty image buffer")

        buf_len = len(image_bytes)
        c_buf = (ctypes.c_ubyte * buf_len).from_buffer_copy(image_bytes)

        with self._lock:
            res = self._lib.process_image_memory(c_buf, buf_len, score_thresh, nms_thresh)
            try:
                if res.error_code != 0:
                    raise RuntimeError(f"C engine error during inference: {res.error_code}")

                output = []
                for i in range(res.count):
                    face = res.faces[i]
                    embedding = np.ctypeslib.as_array(face.embedding).copy()
                    output.append(
                        {
                            "location": [
                                int(face.top),
                                int(face.right),
                                int(face.bottom),
                                int(face.left),
                            ],
                            "encoding": embedding,
                            "det_confidence": float(face.confidence),
                        }
                    )
                return output
            finally:
                self._lib.free_inference_result(ctypes.byref(res))

    def shutdown(self) -> None:
        self._lib.cleanup_engine()

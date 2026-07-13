"""
G.711 A-law (PCMA) codec - wrapper around Python's audioop
"""
import audioop, struct


def alaw_encode(pcm_data):
    """PCM 16-bit signed samples -> G.711a (PCMA) bytes."""
    if isinstance(pcm_data, (list, tuple)):
        pcm_data = struct.pack(f'<{len(pcm_data)}h', *pcm_data)
    return audioop.lin2alaw(pcm_data, 2)


def alaw_decode(data):
    """G.711a (PCMA) bytes -> list of int16 PCM samples."""
    pcm_bytes = audioop.alaw2lin(data, 2)
    n = len(pcm_bytes) // 2
    return list(struct.unpack(f'<{n}h', pcm_bytes))


# G.711 μ-law (PCMU) - use audioop.lin2ulaw / ulaw2lin
def ulaw_encode(pcm_data):
    """PCM 16-bit signed samples -> G.711u (PCMU) bytes."""
    if isinstance(pcm_data, (list, tuple)):
        pcm_data = struct.pack(f'<{len(pcm_data)}h', *pcm_data)
    return audioop.lin2ulaw(pcm_data, 2)


def ulaw_decode(data):
    """G.711u (PCMU) bytes -> list of int16 PCM samples."""
    pcm_bytes = audioop.ulaw2lin(data, 2)
    n = len(pcm_bytes) // 2
    return list(struct.unpack(f'<{n}h', pcm_bytes))


# Aliases for backward compatibility
encode = alaw_encode
decode = alaw_decode


if __name__ == "__main__":
    test = [0, 1, -1, 100, -100, 1000, -1000, 32767, -32768, 5000, -5000]
    enc = encode(test)
    dec = decode(enc)
    max_err = 0
    for o, d in zip(test, dec):
        e = abs(o - d)
        max_err = max(max_err, e)
        print(f"  {o:>6} -> 0x{enc[test.index(o)]:02X} -> {d:>6} (err={e})")
    print(f"  Max error: {max_err}")

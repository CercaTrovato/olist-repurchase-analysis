import os
import hashlib

# ===== 你的绝对路径 =====
DIR_3 = r"MEMBER_INPUT/role03"
DIR_4 = r"MEMBER_INPUT/role04"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(folder, manifest_name, label):
    print(f"\n================ 核验 {label} ================")
    manifest_path = os.path.join(folder, manifest_name)

    if not os.path.exists(manifest_path):
        print(f"❌ 找不到清单文件: {manifest_name}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    ok, bad, miss = 0, 0, 0
    bad_files = []
    miss_files = []

    for line in lines:
        parts = line.split(maxsplit=1)
        if len(parts) != 2: continue

        expected_hash, filename = parts[0], parts[1].strip()

        # 兼容 3号清单里的 * 号前缀
        if filename.startswith("*"):
            filename = filename[1:]

        # 兼容路径斜杠
        filename = filename.replace("/", os.sep).replace("\\", os.sep)
        filepath = os.path.join(folder, filename)

        if not os.path.exists(filepath):
            miss += 1
            miss_files.append(filename)
            continue

        actual_hash = sha256_file(filepath)
        if actual_hash == expected_hash:
            ok += 1
        else:
            bad += 1
            bad_files.append(filename)

    print(f"✅ 一致: {ok} | ❌ 不符: {bad} | ⚠️ 缺失: {miss} | 总计: {len(lines)}")

    if bad > 0:
        print("【不符的文件】:")
        for b in bad_files: print(f" - {b}")
    if miss > 0:
        print("【缺失的文件】:")
        for m in miss_files: print(f" - {m}")


# 执行核验
verify_manifest(DIR_3, "ROUND3_CHECKSUMS.sha256", "3号 (Round3_role03)")
verify_manifest(DIR_4, "CHECKSUMS.sha256", "4号 (Role04_Round3)")

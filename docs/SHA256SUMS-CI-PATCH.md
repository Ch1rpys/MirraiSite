# 产品仓库 CI 补丁：`SHA256SUMS`（跨仓依赖 · M2）

> 目的：官网 `/download` 页展示「Release 附带的 `SHA256SUMS` 文件」——标准格式一份，用户可 `sha256sum -c` 校验。
> 现状：`.github/workflows/release.yml` 已为每个安装包生成 `.sha256`（`<file>.sha256`），
> 但缺一个**聚合的标准 `SHA256SUMS` 文件**。本补丁只加一个汇总 job，不动现有构建步骤。
> 合并方式：人工 review 后把下面的 job 追加到 `release.yml` 末尾即可。

---

## 追加到 `.github/workflows/release.yml`（与 `macos-app` / `windows-app` 平级）

```yaml
  checksums:
    name: Aggregate SHA256SUMS
    needs: [macos-app, windows-app]
    # 两边都成功才汇总；单平台失败时不产出 SHA256SUMS，避免文件残缺
    if: success()
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Build SHA256SUMS from the per-file checksums
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG="${{ inputs.tag || github.ref_name }}"

          # 下载该 release 上的全部资产（含 .sha256 与安装包本体）
          mkdir -p assets
          gh release download "$TAG" --dir assets

          # 校验每份 .sha256 与安装包是否一致（防上传错位）
          cd assets
          for sum in *.sha256; do
            [ -f "$sum" ] || continue
            # .sha256 里可能是带路径的文件名，归一化成 basename 后校验
            base=$(awk '{print $2}' "$sum" | xargs basename)
            expected=$(awk '{print $1}' "$sum")
            actual=$(sha256sum "$base" | awk '{print $1}')
            if [ "$expected" != "$actual" ]; then
              echo "::error::checksum mismatch for $base" >&2
              exit 1
            fi
            echo "$expected  $base"
          done > SHA256SUMS

          echo "SHA256SUMS:"
          cat SHA256SUMS

          gh release upload "$TAG" SHA256SUMS --clobber
```

---

## 说明

1. **格式**：`<sha256>␣␣<文件名>`（GNU `sha256sum` 默认格式，macOS `shasum -c` 也认）。
   只收**安装包**（`.dmg` / `.exe`），不含 Docker（Docker 展示镜像 digest，见官网下载页口径）。
2. **幂等**：`--clobber`，重跑 job 会覆盖旧的 `SHA256SUMS`。
3. **失败面**：`needs: [macos-app, windows-app]` + `if: success()`——任一平台失败则不产出，
   官网侧展示逻辑已按「找不到 SHA256SUMS 就只给链接」降级。
4. **顺序**：两个平台 job 并行上传各自的 `.sha256`，本 job 在其后聚合；不改现有上传步骤，
   合并冲突面为零。
5. 合并后请发一个新版本（或对旧版本手动跑一次 `workflow_dispatch`）验证 `SHA256SUMS` 出现在 Release 资产里。

---

## 验收（合并后）

```bash
gh release download v1.3.0 --pattern SHA256SUMS
sha256sum -c SHA256SUMS        # 全部 OK
shasum -a 256 -c SHA256SUMS    # macOS 同样全部 OK
```

官网 `/download` 页展示该文件中每个安装包的 SHA-256（构建时 `scripts/fetch-releases.mjs` 已拉取
Release 资产列表；若要展示具体哈希值，可在该脚本里额外下载 `SHA256SUMS` 解析——当前先链接到 Release）。

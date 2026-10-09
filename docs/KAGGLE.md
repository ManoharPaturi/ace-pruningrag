# Kaggle execution

Kaggle is the selected remote compute target. The initial job validates GPU arithmetic, the pinned dataset, the upstream setup audit, and offline BM25 retrieval. It does not download model weights or claim a PruningRAG reproduction.

The builder embeds only allowlisted first-party Python sources and experiment JSON configurations. It does not upload the private GitHub token, Kaggle token, raw data, caches, or upstream code. The job independently downloads the public pinned dataset and upstream checkout. Raw data and the checkout stay in `/tmp`; small result artifacts go to `/kaggle/working/phase1`.

Use one authenticated account for the first job. Additional API keys are not needed for this bounded bootstrap.

```bash
uv run --no-editable python scripts/build_kaggle_kernel.py --owner YOUR_KAGGLE_USERNAME --output runs/kaggle/kernel-v1
uv tool run --from kaggle==2.2.4 kaggle kernels push -p runs/kaggle/kernel-v1 --accelerator NvidiaTeslaT4 -t 900
uv tool run --from kaggle==2.2.4 kaggle kernels status YOUR_KAGGLE_USERNAME/ace-pruningrag-phase1-bootstrap
uv tool run --from kaggle==2.2.4 kaggle kernels output YOUR_KAGGLE_USERNAME/ace-pruningrag-phase1-bootstrap/1 -p runs/kaggle/output-v1
```

The generated metadata requests a private kernel, internet access, and dual T4 acceleration. Availability depends on the account and scheduler; only downloaded hardware and completion artifacts verify what actually ran. Kernel submission, kernel completion, and baseline reproduction are different states.

The full baseline still requires the original domain-router adapter, a compatible mock API server and snapshot, the chosen Llama checkpoint, BGE models, and an explicit target experiment. Hosting inference on the same Kaggle machine avoids forwarding local credentials. If later provider access is necessary, use Kaggle Secrets rather than notebook code or metadata.

Official references: [kernel commands](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md) and [kernel metadata](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md).

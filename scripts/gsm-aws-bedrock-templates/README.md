# Google Secret Manager — two Bedrock key files

GSM **secret names** (fixed; the app looks these up in prod):

| Secret name in GCP              | What to store                          |
|--------------------------------|----------------------------------------|
| `aws-access-key-id`            | AWS access key ID only (e.g. `AKIA…`)  |
| `aws-secret-access-key`        | AWS secret access key only (long)      |

## Rename / fill in locally

1. Copy the templates to **`.value`** files (gitignored — do not commit):

   ```bash
   cd scripts/gsm-aws-bedrock-templates
   cp aws-access-key-id.TEMPLATE aws-access-key-id.value
   cp aws-secret-access-key.TEMPLATE aws-secret-access-key.value
   ```

2. Edit each **`.value`** file: put the real key on **one line** (remove `#` comment lines, or the upload script will skip them).

3. From the **repo root**, upload to GSM:

   ```bash
   export GCP_PROJECT_ID=your-gcp-project
   ./scripts/gsm-aws-bedrock-upload-two-secrets.sh
   ```

4. On the VM, keep **`SAILLY_ENV=prod`**, **`GCP_PROJECT_ID=...`**, and **do not** set `GSM_AWS_BEDROCK_COMBINED_SECRET` if you use this two-secret layout.

**Note:** You cannot “rename” an existing secret like `AwsHaiku` in place. Either add new secrets with the names above, or use `GSM_AWS_BEDROCK_COMBINED_SECRET=AwsHaiku` with a JSON value (see `server/configs/secrets.py` docstring).

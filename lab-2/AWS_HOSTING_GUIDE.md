# My Guide: How I Hosted My Static Website on Amazon S3 (AWS Academy)

In this guide, I will walk you through the steps I took to upload and host my Lab 2 files as a static website using Amazon S3 within the AWS Academy environment.

## My Prerequisites
- I have access to my **AWS Academy Learner Lab**.
- I have all my website files (`index.html`, `404.html`, `styles.css`, `script.js`, and SVG images) ready in my local project folder.

---

## Step 1: How I Created My S3 Bucket

1. First, I log into my **AWS Academy** account and click on **AWS Console**.
2. Once I'm in the AWS Management Console, I search for **S3** and open the S3 dashboard.
3. I click the **Create bucket** button to start the process.
4. For the **Bucket name**, I enter a unique name like `nimbusworks-static-site-[my-name]`.
5. I ensure the **AWS Region** is set to `us-east-1` (N. Virginia), which is the default for my lab.
6. I leave the **Object Ownership** as "ACLs disabled (recommended)".
7. In the **Block Public Access settings**, I do the following:
   - I **uncheck** "Block all public access".
   - I check the box to acknowledge that I understand these settings might make my bucket public.
8. Finally, I scroll down and click **Create bucket**.

---

## Step 2: How I Enabled Static Website Hosting

1. I click on the name of the bucket I just created to open its configuration.
2. I navigate to the **Properties** tab.
3. I scroll all the way down to the **Static website hosting** section and click **Edit**.
4. I select **Enable**.
5. For the **Hosting type**, I choose "Host a static website".
6. In the **Index document** field, I type `index.html`.
7. In the **Error document** field, I type `404.html`.
8. I then click **Save changes**.

---

## Step 3: How I Configured My Bucket Policy

Even though I unchecked "Block Public Access", I still need to explicitly allow public read access via a policy.

1. I go to the **Permissions** tab of my bucket.
2. I scroll down to the **Bucket policy** section and click **Edit**.
3. I copy and paste the following policy into the editor:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::MY_BUCKET_NAME/*"
        }
    ]
}
```

4. **Note**: I make sure to replace `MY_BUCKET_NAME` with the actual name of the bucket I created.
5. I click **Save changes**.

---

## Step 4: How I Uploaded My Files

1. I go back to the **Objects** tab of my bucket.
2. I click the **Upload** button.
3. I drag and drop all the files from my local folder into the upload window:
   - `index.html`
   - `404.html`
   - `styles.css`
   - `script.js`
   - `error-cloud.svg`
   - `hero-cloud.svg`
   - `icon-access.svg`
   - `icon-hosting.svg`
   - `icon-storage.svg`
   - `logo-mark.svg`
4. I click the **Upload** button at the bottom of the page and wait for it to finish.
5. Once complete, I click **Close**.

---

## Step 5: How I Accessed My Live Website

1. I return to the **Properties** tab of my bucket.
2. I scroll down to the **Static website hosting** section.
3. I find the **Bucket website endpoint** URL and click on it.
4. My website (e.g., `http://my-bucket-name.s3-website-us-east-1.amazonaws.com`) is now live!

I have successfully deployed my static site to the cloud!

# Astronomium: GitHub to Vercel, using only your browser

Use `releases/astronomium-github-browser.zip`. This is a deployment snapshot of the complete built course, packaged for GitHub's browser uploader. It contains 12 upload files, including seven numbered data parts. Each part is at most 20 MiB; GitHub allows 25 MiB per browser-uploaded file.

You do not need to install or run Python, Node, Git, Vercel CLI, or any other application on your computer. The build command below runs on Vercel's servers. Windows File Explorer can extract the ZIP.

## 1. Extract the package

1. Right-click `astronomium-github-browser.zip` in File Explorer and choose **Extract All**.
2. Open the extracted folder containing `build.py`, `bundle-manifest.json`, `vercel.json`, `README.md`, `.gitignore`, and `site-001.part` through `site-007.part`.
3. Keep the numbered `.part` files as they are. Do not try to open, rename, or extract them. They contain all the course pages, models, textures, mathematics, and questions.

## 2. Create your GitHub repository

1. Sign in to [GitHub and create a repository](https://github.com/new?name=astronomium&visibility=private).
2. Select your personal account as the owner and name the repository **astronomium**. A private repository is suitable; the published website can still be public. Vercel Hobby does not support private repositories owned by GitHub organizations, so use your personal account for this route.
3. Leave the options to add a README, `.gitignore`, and license unselected; this package includes its own README and `.gitignore`.
4. Click **Create repository**.
5. On the empty repository page, select **uploading an existing file**. If the repository already contains a file, use **Add file → Upload files**.
6. Upload **only `site-001.part`**, wait for the upload to finish, and click **Commit changes**. Wait until that file appears on the repository's main page.
7. Use **Add file → Upload files** to upload `site-002.part` by itself and commit it. Repeat separately for `site-003.part` through `site-007.part`: **one data part per commit**. Keep every file at the repository root, not inside an enclosing folder. Do not upload the outer ZIP.
8. Once all seven parts are committed, upload `build.py`, `bundle-manifest.json`, `vercel.json`, and `README.md` together and commit them. You can also include `.gitignore` if the uploader accepts it; this optional file is not needed to deploy.
9. Check that `vercel.json`, `build.py`, `bundle-manifest.json`, and all seven numbered parts are visible together on the repository's main page. Finish these uploads before connecting Vercel. If Vercel is already connected, an automatic build of an incomplete upload may fail; evaluate the build after the final files have been committed.

**Upload correction:** submitting the entire approximately 140 MB kit in one browser commit failed with GitHub's "file is too large" message, despite every individual file being below its documented 25 MiB limit. The message did not identify a particular file or establish an aggregate limit. The separate-commit procedure above reduces each large upload to at most 20 MiB; its success in your GitHub account still needs to be confirmed. If `site-001.part` alone fails, stop and retain the exact error rather than retrying the full batch.

GitHub displays `.part` files as binary files; that is expected. Uploading the outer ZIP alone does not extract the site into the repository.

## 3. Connect Vercel

1. Open [Vercel New Project](https://vercel.com/new) in your browser.
2. Connect your GitHub account if it is not connected already. When GitHub asks which repositories Vercel may access, you can select only **astronomium**.
3. Find **astronomium** under **Import Git Repository** and click **Import**.
4. Confirm the settings below. The included `vercel.json` supplies the build settings; dashboard overrides are normally unnecessary.

| Setting | Value |
| --- | --- |
| Project name | `astronomium` or another available name |
| Framework preset | **Other** |
| Root directory | Repository root (`./`) |
| Build command | `python3 build.py` |
| Output directory | `dist` |
| Install command | Empty; dependency installation is disabled by `vercel.json` |
| Environment variables | None required |

5. Click **Deploy**. Vercel downloads the repository, verifies and joins the seven parts, and creates the complete static site online.
6. When deployment succeeds, click **Visit**. Vercel assigns a `.vercel.app` address; the exact name depends on availability and your project settings.
7. Check the homepage, a lesson, a laboratory, practice, the study guide, and the equation reference. Refresh a direct lesson URL to confirm direct links work.

Do not select Vite for this particular upload kit. The course was already built with Vite; this deployment command restores that verified build without installing dependencies. Do not use Vercel Drop for these files.

Your earlier `api-upload-free` error was a Vercel upload rate limit. Git integration avoids uploading thousands of files from your browser, but it does not reset an existing account limit. If Vercel reports that same error again, wait until the displayed reset time before retrying.

## What this package contains

This kit restores the complete 9,699-file static release. It retains the existing course, question banks, textures, mathematics resources, study guide, equation reference, and hosting headers. The build verifies every data part, the joined ZIP, and each extracted asset against recorded SHA-256 hashes. Missing or corrupted parts stop the build with an explanatory error.

This is a **deployment snapshot**, rather than the editable TypeScript source repository. Keep the original project and source archive for development. For future releases, replace the seven numbered parts and the matching manifest together on a branch, and merge only once the upload is complete. A new commit to the connected production branch triggers a Vercel deployment.

No course account or backend database is required. Learner progress remains in each learner's browser. This package creates no operating-system or sandbox accounts.

Developed by Jan Skvaril for educational and entertainment purposes. Accuracy is not guaranteed; verify calculations and conclusions independently. This deployment kit preserves the course's existing credits and notices.

## Optional: use the same repository with Cloudflare Pages

Create a **Pages** project using **Connect to Git**, choose this repository, select framework **None**, set build command `python3 build.py`, and output directory `dist`. Python is included in the Pages build image. No installation command or environment variables are required. Connect through Pages rather than the static-file drag-and-drop screen, which rejected this course's file count. If your existing project was created using Direct Upload, create a new Git-connected Pages project.

## References

- [GitHub: create a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
- [GitHub: browser upload limits and workflow](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [Vercel: import a Git repository](https://vercel.com/docs/git)
- [Vercel: build settings](https://vercel.com/docs/builds/configure-a-build)
- [Vercel: build environment](https://vercel.com/docs/builds/build-image)
- [Vercel: limits](https://vercel.com/docs/limits)
- [Cloudflare Pages: Git integration](https://developers.cloudflare.com/pages/get-started/git-integration/)
- [Cloudflare Pages: build environment](https://developers.cloudflare.com/pages/configuration/build-image/)

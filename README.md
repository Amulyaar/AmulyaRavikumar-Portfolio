# Amulya Ravikumar portfolio

A static portfolio built with HTML, CSS, and JavaScript. No build command or framework installation is required.

## Files to publish

Upload the contents of this folder, not the folder itself, to the root of a GitHub repository. Keep `index.html`, `styles.css`, `app.js`, and `favicon.svg` together.

The export includes only the public website files. The GPA was removed because the supplied resume versions disagree; add it back only after checking your transcript. Review all dates, metrics, links, and contact details before publishing.

## Publish on GitHub Pages

1. Create a public repository named `<your-github-username>.github.io` on GitHub. Replace the placeholder with your exact GitHub username.
2. Upload the four site files to the repository root and commit them. Do not upload the ZIP itself.
3. In the repository, open **Settings → Pages**. Under **Build and deployment**, choose **Deploy from a branch**, then `main` and `/(root)`, and save.
4. After publication, your temporary address is `https://<your-github-username>.github.io`.

You can instead use any repository name, but its temporary address will contain the repository name. The site uses relative asset paths, so either approach works.

## Connect a domain you own

1. Buy or use a domain you control, such as `example.com`.
2. In your GitHub repository, open **Settings → Pages → Custom domain**, enter the domain, and save. GitHub creates a `CNAME` file when you publish from a branch. Add the domain to GitHub before changing DNS.
3. At your domain registrar, create four `A` records for host `@`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, and `185.199.111.153`.
4. Add a `CNAME` record for host `www` pointing directly to `<your-github-username>.github.io` (no repository name). Remove conflicting old records for `@` and `www`.
5. Wait for DNS and the GitHub Pages certificate, then enable **Enforce HTTPS** in Settings → Pages.

If you choose `www.example.com` as the primary address instead, set that in GitHub Pages; GitHub can redirect the apex domain when both records are configured correctly.

Official documentation:
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https

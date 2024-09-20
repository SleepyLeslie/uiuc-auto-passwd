# UIUC Password Resetter

This tool helps you quickly reset your UIUC password.

## But why?

UIUC IT scrambles your password when their "security monitoring" thinks your account "may be compromised". When this happens, they would shoot you an email with the title "Compromised Account - <netid>" and the following contents:

```
Security monitoring indicates that your University of Illinois account may be compromised. Your Active Directory/NetID password was scrambled as a safety measure. This automated notification is being sent to your University of Illinois email address and your non-University email address, if registered.

To regain access to your account you may do so with the Technology Services Password Manager, accessible at https://go.illinois.edu/password, or using the "Reset Your Password" link on the main Technology Services website.

If you have not set up your account recovery options and need assistance, or if you would like to verify the authenticity of this email, please contact the Technology Services Help Desk by calling 217-244-7000 or by emailing consult@illinois.edu. Additionally, if you have questions about this process or what may have caused this password reset, please view the Knowledge Base article at https://answers.uillinois.edu/illinois/63517.

The suspicious activity that triggered this alert for user <netid> is listed below:

<netid> was observed logging in from two different locations within a period of time that makes travel between them impossible. 

First login:
Activity observed at: <time>
Access: uiuc-shibboleth-default |  | windows.azure.active.directory
IP Address: <IP>, located in Portland Oregon United States

Second login:
Activity observed at: <time>
Access: uiuc-shibboleth-default |  | windows.azure.active.directory
IP Address: <IP>, located in Johannesburg Gauteng South Africa

AUTO:CAA
```

This email genuinely demonstrates their extremely good understanding of computer security, and has struck me with unprecedented awe and respect 20+ times in the past year. Each time this happens, I would need to go to their NetID center, click on "forgot password", pass the enormously helpful and secure Duo authentication which surprisingly supports Passkeys (thank God!) and wait for an email containing a reset link to hit my personal email inbox. Then I have to follow the link to set a new password, which cannot contain any of these characters: `'@",`. It seems UIUC IT truly understands SQL injection attacks and has employed the most effective and clever defense against it, but unfortunately the incompetent open-source password manager I use, Bitwarden, often generates random "strong" passwords that fail to meet UIUC's standards. After resetting the password, I have to remember to update the WiFi password stored in NetworkManager and all my mobile devices. To make things even more wonderful, I have to wait up to half an hour until the new password is synchronized to Micro$oft before I can regain full access to UIUC systems. Once upon a time I missed an important email due to this long wait, but it was totally my fault to have let an attacker hack into my university account from South Africa. I hope you all can appreciate together with me how advanced UIUC's infrastructure is, and show some gratitude for their hard work to achieve and maintain supreme security. Without their efforts, my account would have been compromised 20+ times within a year, because I am too paranoid to let Micro$oft know all IP addresses I use, and always use a VPN with a rotating exit node. Despite my sincere compliments (I think I emailed them twice about this), UIUC IT has been faithfully upholding their security standards and would not relax these intricate cutting-edge security measures no matter what. Thus, I figured out that I obviously don't know anything about security at all, and must study harder to protect myself from such intense attacks. Hence I created this little tool to educate myself more about security, for example how Duo collects your browser fingerprint during authentication, which is an undoubtedly useful mechanism that really values your privacy.

## What is this tool?

Currently it is only a Proof of Concept showing that I can automate the password resetting process. More commits will be added to make it a more customizable tool. For now, it:
- Requires you to specify your NetID in a config file,
- Generates a TOTP code to authenticate with Duo (Duo is simply TOTP/HOTP with the setup key hidden behind some proprietary APIs that have been reverse engineered anyways),
- Requests a password reset email,
- Connects to your IMAP server,
- Locates the requested email,
- Generates a secure password (also secure by UIUC's definitions),
- Resets your password and shows it to you.

The following features are planned:
- Bitwarden integration to update the saved password(s).
- NetworkManager integration.

If you find this idea useful but you use a different setup than mine, say you prefer Duo push notifications (but seriously, why?) or use a personal email address that does not support IMAP for whatever reasons (e.g. proton free plan), feel free to raise feature requests and I will be happy to extend this tool.

## TOTP

UIUC supports Duo TOTP since June 2024. To set it up, use the same HOTP key as your TOTP key, 30 seconds as the refresh interval and 6 digits as the length. This script auto-generates TOTP codes, making it stateless.

# Enable Cloud Firestore API

## Issue
You're seeing this error:
```
Cloud Firestore API has not been used in project finallineup-117a0 before or it is disabled
```

## Solution: Enable the API

### Quick Fix (2 minutes)

1. **Click this link** (or copy-paste into browser):
   ```
   https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=finallineup-117a0
   ```

2. **Click "Enable" button** (big blue button at the top)

3. **Wait 1-2 minutes** for the API to propagate

4. **Test again** - the errors should disappear

### Alternative Method

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select project: **finallineup-117a0**
3. Go to **APIs & Services** → **Library**
4. Search for **"Cloud Firestore API"**
5. Click on it
6. Click **"Enable"**
7. Wait 1-2 minutes

## Verify It's Enabled

After enabling, you can verify:
1. Go to [APIs & Services → Enabled APIs](https://console.cloud.google.com/apis/dashboard?project=finallineup-117a0)
2. Look for **"Cloud Firestore API"** in the list
3. Status should be **"Enabled"**

## After Enabling

Once enabled:
- ✅ Firestore operations will work
- ✅ Data will persist
- ✅ No more 403 errors
- ✅ Collections will be created automatically

## Note

Even though you enabled Firestore Database in Firebase Console, you also need to enable the **Cloud Firestore API** in Google Cloud Console. They're related but separate steps.

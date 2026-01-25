# Create Firestore Database

## Issue
You're seeing this error:
```
The database (default) does not exist for project finallineup-117a0
```

This means the Firestore database hasn't been created yet in your Firebase project.

## Solution: Create the Database

### Quick Fix (2 minutes)

1. **Click this link** (or copy-paste into browser):
   ```
   https://console.cloud.google.com/datastore/setup?project=finallineup-117a0
   ```

2. **OR go to Firebase Console:**
   - Visit: https://console.firebase.google.com/project/finallineup-117a0/firestore
   - Click **"Create database"** button

3. **Choose database mode:**
   - Select **"Start in test mode"** (for development)
   - Click **"Next"**

4. **Choose location:**
   - Select a location closest to your users (e.g., `us-central1`, `us-east1`)
   - Click **"Enable"**

5. **Wait 1-2 minutes** for the database to be created

## Verify Database is Created

After creating, you should see:
- ✅ Database appears in Firebase Console
- ✅ No more 404 errors in logs
- ✅ Collections can be created automatically when you use endpoints

## What This Does

- Creates the actual Firestore database instance
- Enables data storage
- Allows collections to be created automatically
- Fixes the "database does not exist" error

## Important Notes

1. **Test Mode**: If you chose "test mode", the database allows read/write for 30 days. After that, you'll need to set up security rules.

2. **Location**: Once set, the location cannot be changed. Choose wisely based on where your users are.

3. **Free Tier**: Firestore has a generous free tier (50K reads/day, 20K writes/day, 20K deletes/day).

## After Creating Database

Once created:
- ✅ No more 404 errors
- ✅ Data will persist
- ✅ Collections created automatically
- ✅ All Firestore operations will work

## Troubleshooting

If you still see errors after creating:
- Wait 2-3 minutes for propagation
- Check Firebase Console to confirm database exists
- Verify FIREBASE_CREDENTIALS is set correctly in Render
- Check Render logs for any other errors

# caloryTrackerWebapp

Small, self-hostable calory/exercise/weight tracker flask application.

![kuva](https://github.com/user-attachments/assets/508f2f98-e1f9-4aa6-8cc2-cc1852a1ad39)
![kuva](https://github.com/user-attachments/assets/e7df3bfc-2b66-48e0-8346-9eeaf0c87ae1)
![kuva](https://github.com/user-attachments/assets/ee4ceb80-d0d6-4fba-bc4e-46d21bf0b6a4)


## Things to be done (in no particular order):
- Change deletion logic to use ids. The current approach is dumb though should work as long as user does not have two entries with the exact same timestamp
- Weekly/monthly views for records
- Ability to delete weight values
- Improve error handling. Currently if something goes wrong error is only logged to browser console (if even that)
  
## ThirdParty content used:
- https://blog.getbootstrap.com/2024/02/20/bootstrap-5-3-3/
- https://jquery.com/
- https://docs.python.org/3/library/sqlite3.html
- https://flask.palletsprojects.com/en/stable/

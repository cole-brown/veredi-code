This is for testing `veredi.run.registry` being able to find registration files
for Registrars, Registries, and Registrees.

The important thing we're testing is that it ignores files and folders that it
should be ignoring. For example, don't look in '.git/' since there's a billion
files in there in the real '.git' folder.

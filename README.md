# Automatic Leaderboard Maker

Scrapes, saves, and publishes a leaderboard on the 
[Top 100 Posters, round 2](https://tbgforums.com/forums/index.php?topic=5703) topic.

This tool (further called ALM) scrapes the TBG's 
[memberlist](https://tbgforums.com/forums/index.php?action=mlist), and posts the results 
as a leaderboard of the aforementioned "Top 100 Posters, round 2" topic. The current 
leaderboard is also saved as a reference for the post count difference on the next run 
of this script.

## Simulation
In case where you want to see what the leaderboard looks like without publishing or saving 
anything, you can simulate them with the `--simulate` switch.

## Messages
You can attach/include a message to the generated leaderboard. ALM will read the file
`message.txt` if present, and includes its contents below the leaderboard.

You can choose another file with the `--message` switch.

## Exclude list
ALM can exclude TBGers that chooses to be opted out on the leaderboard. The `exclude.txt`
file contains a list of user IDs that ALM will not include on the leaderboard.

You can choose another file with the `--exclude-file` switch.

## Leaderboard Maker 2 Specification
ALM generates a leaderboard under the Leaderboard Maker 2 format.
The leaderboard consists of several lines. The lines are formatted as such:
```
TTT DDD AAAA xxx. Name #Post (Diff)
```
### Name
`Name` is the user's name. They are left-justified so the `#Post` values after it are aligned.

### Position
`TTT` is the user's position/status. Their possible values are:
- `TEA` for the TBG Teams
- `RET` for retired TBG managers
- `TBG` for TBGers and New TBGers
- `BAN` for banned TBGers (note that the memberlist doesn't show banned TBGers)
- `OTH` for other TBGer positions.

### Rank difference
`DDD` represents the user's change of rank from the previous leaderboard. 
They are represented by an arrow (showing direction) and a number (showing amount).
One example is `↑ 1` (meaning rank up 1, e.g. from third to second).
A special case `===` is used when there's no change of rank.

### Post counts
`#Post` is the user's current post count, at the time of scraping.

`Diff` is the difference of the current post count and the previous leaderboard's count.

`AAAA` represents the user's activity. It is a visual representation of the `Diff` value.
It is comprised of 3 Braille symbols, and one symbol being a space, a dot, or a two-dot.
These are picked because they're all comprised of dots.

For the first character, a single dot represents 10 posts per month, where 1 month is the
distance between the current and previous leaderboard. (the update interval is 1 month)
For the later characters, a single dot represents the full capacity of the previous character.

Here's an example of them:
```
⡀⠀⠀  : 10 ppm
⡄⠀⠀  : 20 ppm
⡆⠀⠀  : 30 ppm
⡇⠀⠀  : 40 ppm
⣿⠀⠀  : 80 ppm
⣿⡀⠀  : 160 ppm
⣿⡄⠀  : 240 ppm
⣿⡆⠀  : 320 ppm
⣿⡇⠀  : 400 ppm
⣿⣿⠀  : 720 ppm
⣿⣿⡀  : 1440 ppm
⣿⣿⡄  : 2160 ppm
⣿⣿⡇  : 3600 ppm
⣿⣿⣿  : 6480 ppm
⣿⣿⣿. : 12960 ppm
⣿⣿⣿: : 19440 ppm
(ppm means posts per month)
```
A special case `⣏⣉⣉]` is used when no past activity is found. (for `Diff` = `N/A`)

## Scheduling ALM
When run, ALM only makes a single leaderboard. It does not run continuously, making
leaderboards monthly. To do that automatically, you need a job scheduler to run ALM monthly.

Most OSes offer a built-in job scheduler. Here's how you can set them up to run ALM.

### Windows
(warning: untested)

Windows offers (Task Scheduler)[https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page]
as their job scheduler. To make a task for ALM, do the following:
- Open Control Panel > Administrative Tools > Task Scheduler.
  - On older Windows versions, you may find Task Scheduler on "Accessories and System Tools".
  - Alternatively, you can run `taskschd.msc` on the Run prompt.
- On the Actions bar, select Create Basic Task. Give the task a name, then click Next.
- On the Trigger section, choose Monthly. Choose the first day of the month.
- On the Action section, choose Start a program. Click Next.
- Supply "Program/script" with the location where you stored `scheduler/autolm.bat`.
- Supply "Start in" with the location where you stored ALM. Click Next.
- Confirm the summary, then click Finish to accept.

### Linux and other Unix-likes
There are two ways to schedule ALM on Unix-likes. 
One uses `cron` and the other uses `systemd` timers.

#### Using cron
`cron` (and others like them) is a simple job scheduler that is available in most Linux
distributions and other Unix-likes. To set up a job for ALM, do the following:
- On a terminal, run `crontab -e` to edit your crontab.
  - You may need to install `cron` or similar if this command is not available.
- Add this line: `0 0 1 * * /usr/bin/env -C /path/to/alm USERNAME=Leaderboarder PASSWORD=opensesame python main.py`
- Save and exit the editor.

#### Using systemd timers
If your system has `systemd` (which includes most Linux distros), you may add a timer to start
ALM. To add it, do the following:
- Using root, copy the files `scheduler/autolm.service` and `scheduler/autolm.timer`
  to `/etc/systemd/system`.
- Edit the service by running `systemctl edit autolm.service` under root.
  - Change `/path/to/alm` with the location where you stored ALM.
  - Change the Environment values as well.
  - You may change the location of the Python executable in `ExecStart`.
  - Save and exit the editor.
- If desired, you can add `Persistent=true` to `scheduler/autolm.timer`. 
  This will start ALM immediately when it missed the last start time.
  This is useful for machines that doesn't stay on.

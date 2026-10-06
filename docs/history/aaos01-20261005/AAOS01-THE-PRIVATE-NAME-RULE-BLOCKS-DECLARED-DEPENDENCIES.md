# AAOS-01: the private-name rule blocks the declared dependencies from being staged

## 1. What I set out to do

The receipt's last section names one incomplete item: no candidate was restaged with its dependencies and
the pdf and image capabilities rerun, so their callability inside a candidate is still unverified. It also
names the instrument that was not used - the staging script's dependency source and dependency list - so the
intended action is to stage a candidate with those dependencies.

## 2. What happened when I did exactly that

First attempt, pointed at the runtime I had assembled earlier, failed with linked staging path rejected.
Investigating showed the cause was my own earlier work: six junctions I had created by hand inside that
runtime. The dependency source and the workers tree were clean. So I switched to the registered bare
CPython that the receipt itself names, which has zero reparse points.

Second attempt got past the link rule and failed at the next one with protected staging path. I read the
rule. It lowercases the absolute path, splits it on separators, and rejects the path if ANY component is in
a private-name set or starts with .env. I then tested my five input paths directly against the rule - all
five pass. So the offending component is inside the copied content, not in my arguments.

Scanning the copied distributions for the declared dependencies found this:

| distribution | offending component | relative path |
| --- | --- | --- |
| fastapi | .agents | fastapi/.agents |
| litellm | auth | litellm/proxy/auth |
| litellm | auth | litellm/proxy/agent_endpoints/auth |
| litellm | auth | litellm/proxy/_experimental/mcp_server/auth |

## 3. Why this is a real conflict, not my mistake

The private-name set exists to keep agent-private state and credentials out of a distribution. Its members
include .agents and auth. Both are reasonable names to protect.

But the rule matches on a path component's name alone. fastapi ships a directory called .agents, and litellm
ships directories called auth. Neither is agent-private state and neither holds credentials - they are
ordinary upstream package directories that happen to collide with the protected names.

So staging a candidate with the declared dependency list necessarily fails, as long as the list includes
fastapi or litellm. The rule cannot currently distinguish an upstream directory from the private state it
means to protect.

## 4. A possible reason the item stayed incomplete

I suggest, as an inference and not as established fact, that this is why the dependency-staged candidate was
never produced: not an oversight, but that the correct procedure is blocked by this rule. I have not checked
whether anyone attempted it and recorded the same failure.

## 5. What I am NOT doing

I am not modifying the rule, the staging script, or the private-name set. Changing a security boundary is a
governed decision, not an executor convenience, and a name-collision fix needs a design (match on location
and role rather than on name alone) that belongs in a reviewed change. I am also not staging a candidate
with those directories removed, since that would ship something different from the declared dependencies.

## 6. Ledger note

This is the first concrete obstacle found on the path the receipt names as next. It is recorded rather than
worked around, because the workaround would silently change what is being shipped.

## 7. What changed this round

Nothing but this document and my own probe scripts under project-local. Read-only against repository
sources; the staging attempts wrote only under project-local and the temporary target directory.
No repository source file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.

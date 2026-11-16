Clipdesk Missions: product design document




  Clipdesk Missions: product design document
    Nov 17, 2026

  Draft for human review.


  The idea
  Clipdesk Missions designs the Short before the game is played. Every clipper on the
  market hunts for highlights after a stream ends. This platform hands the gamer a mission
  that already has a hook, a win condition and a title, then cuts the Short from the exact
  minutes that mission ran.

  Three parts make it different, and no current tool combines them.

     1. Questions in, missions out. The platform mines what people are asking about GTA 6,
        such as "can you outrun five stars on a bicycle?". Each question becomes a playable
        mission. Each Short answers something people are already searching for.
     2. Clips by design, not by detection. The gamer taps Start and Done on a phone. The
        platform knows the exact window, so it never guesses. The stream passes through
        the platform, so the Short is ready minutes after Done, while the stream is still live.
     3. One shared Daily Mission. Every creator on the platform gets the same mission each
        day. Attempts are scored and ranked on a public leaderboard. That is the community,
        and the pooled results are data no single channel has.

  The format can be copied. The pooled results and the creator community cannot, so they
  are the moat. Nobody can promise that no one else builds this, and no design guarantees
  views or revenue.


  Why this idea and not the obvious ones
  Mission-first is the only option that works on launch day, stays monetisable and builds a
  network.




                                                                                             Page 1 of 16
Clipdesk Missions: product design document




     Option                                  Verdict           Reason

     Better highlight detection              Rejected as the   Eklipse, OpusClip and others already
                                             core              compete here. Game-specific
                                                               detectors for GTA 6 cannot exist
                                                               before launch. Viewers cannot see the
                                                               difference.

     AI-written commentary script            Rejected          Scripted lines kill real reactions. AI
                                                               narration over gameplay is the pattern
                                                               YouTube stopped monetising in July
                                                               2026.

     Clipping other streamers                Rejected          Reused content. You own nothing and
                                                               depend on someone else's stream.

     Fully automatic faceless                Rejected          Template-based mass uploads are the
     channel                                                   first category on YouTube's
                                                               unmonetisable list.

     Mission-first with a shared             Chosen            Needs no knowledge of the game's
     Daily Mission                                             screen layout. Produces searchable,
                                                               self-contained Shorts. Gets stronger
                                                               with every creator who joins.


  Launch week favours this in one specific way. On 19 November there is no gameplay trend
  data for GTA 6 yet. There are only questions: what is possible, what breaks, what is hidden.
  The first credible video answers win search and the Shorts feed.

  Missions also remove most of the processing cost. A four-hour stream holds perhaps 40
  minutes of mission windows. The platform transcribes and analyses only those windows.


  The mission loop
  One streaming day is eight steps, and the gamer touches the platform only at steps 2, 4
  and 6.

     1. 05:00, mission pool refresh. The platform collects fresh questions and high-
        performing GTA 6 videos, then writes about 20 candidate missions. This runs once for
        all users.




                                                                                                 Page 2 of 16
Clipdesk Missions: product design document




     2. Gamer opens Today. They see the Daily Mission plus three personal picks. They
        accept, swap or edit. Accepted missions go to the phone remote.
     3. Go live. OBS streams to the platform's address instead of YouTube's. The platform
        records the stream and forwards it to YouTube in the same second.
     4. Start and Done. The gamer taps Start when a mission begins and Done when it ends,
        with a result such as a time, a star count or pass/fail. A voice phrase is the backup.
     5. Clip build. Seconds after Done, the platform cuts that window, finds the payoff, adds
        the hook text and captions, and renders a 9:16 Short.
     6. Approve on the phone. The Short appears in the remote. Approve, retitle or discard.
     7. Post while live. The approved Short goes to YouTube with a line pointing to the live
        stream. The attempt lands on the mission's leaderboard.
     8. Results return. After 48 hours the platform reads views and retention, scores the
        mission and feeds that into tomorrow's pool.

  Two side features use the same loop.

         Chat picks the next mission. The remote can open a 60-second vote between two
         missions. The result becomes the Short's hook.
         Bonus moments. After the stream, a cheap audio pass over the non-mission time
         suggests unplanned moments. This is the old Clipdesk detector, now a secondary
         feature.


  Scope
  Ship in three cuts. Each cut is usable by itself, and the first must work for your own team
  on launch day.


     Cut                     Target          Who uses it      Contains

     v0 Launch               19 November     Your team, one   Mission pool written by the LLM
     kit                                     channel          from a typed list of questions. Today
                                                              page. Phone remote with Start and
                                                              Done. Stream relay and recording.
                                                              Mission clip render. Download the
                                                              Short and post by hand.




                                                                                               Page 3 of 16
Clipdesk Missions: product design document




     Cut                     Target               Who uses it        Contains

     v1 Platform             About two weeks      Invited creators   Google sign-in and channel connect.
                             later                                   Automatic question mining.
                                                                     Approve-and-post to YouTube.
                                                                     Leaderboards and public mission
                                                                     pages. Results feedback.

     v2 Product              After v1 is stable   Paying creators    Billing. Chat votes. Bonus moments.
                                                                     TikTok and Instagram posting.
                                                                     Creator-submitted missions.


  Cut from all three, on purpose.

         AI voice-over and AI-written commentary.
         Downloading videos from YouTube links. The platform already holds the recording, so
         there is nothing to download.
         Kubernetes, microservices, a mobile app and a custom video editor.
         Game-specific screen detectors. Missions make them unnecessary for the core
         product.

  Two days is enough for v0 only if your existing Clipdesk render code is reused as it stands.
  Everything else in v0 is new but small.


  Architecture
  The whole platform is six services on one server, and the stream relay is the piece that
  removes downloads, uploads and local storage.




                                                                                                     Page 4 of 16
Clipdesk Missions: product design document




  system architecture · 11 components

  OBS sends the stream to the relay. The relay saves it to the recording store and forwards
  it to YouTube Live at the same time. Taps from the phone reach the API, which queues a
  job in Postgres. The clip worker takes the job, reads the recording, asks the LLM for the
  payoff and title, and writes the Short back to the store. The line along the bottom is the
  API calling YouTube for trend data, posting and results.


  Tech stack
  Every choice follows three rules: one server, as few moving parts as possible, and tools
  that AI coding agents handle well.


     Layer                          Choice                 Why                     Rejected

     Web app                        Next.js, TypeScript,   One app serves the      A native mobile app
                                    Tailwind, shadcn/ui    dashboard, the phone
                                                           remote and the public
                                                           mission pages. Coding
                                                           agents are strongest
                                                           on this stack.




                                                                                                    Page 5 of 16
Clipdesk Missions: product design document




     Layer                          Choice                   Why                       Rejected

     API and                        Python with FastAPI      The Clipdesk pipeline     A Node backend,
     workers                                                 is already Python. One    which would split the
                                                             language covers the       pipeline
                                                             API and the video jobs.

     Database and                   PostgreSQL for both.     One service to run and    Redis with Celery
     job queue                      Jobs use row locking     back up.
                                    through a library such
                                    as Procrastinate.

     Live ingest                    MediaMTX                 MIT licence. Takes        nginx-rtmp, a custom
                                                             RTMP from OBS,            relay
                                                             records fMP4
                                                             segments, forwards to
                                                             YouTube, and checks
                                                             stream keys through
                                                             an HTTP call
                                                             (comparison).

     File storage                   S3-compatible object     Holds recording           Local or external
                                    storage                  segments and finished     drives
                                                             clips. A lifecycle rule
                                                             deletes raw
                                                             recordings after 7
                                                             days.

     Transcription                  faster-whisper on        Minutes of audio per      Transcribing whole
                                    mission windows only     stream instead of         streams
                                                             hours, so a CPU is
                                                             enough at first.

     Rendering                      FFmpeg with libass       Already built in          A browser-based
                                    captions, layouts as     Clipdesk.                 renderer
                                    JSON templates

     AI model                       One provider behind a    Writes missions and       A self-hosted model,
                                    single interface.        titles and picks the      which needs a GPU
                                    Gemini Flash as the      payoff, with JSON         and upkeep
                                    default.                 output. Gemini also
                                                             reads video directly
                                                             (Google docs).




                                                                                                           Page 6 of 16
Clipdesk Missions: product design document




     Layer                          Choice                  Why                      Rejected

     Trend data                     YouTube Data API v3     Official. Gives search   Google Trends API,
                                                            results, video           which is still a gated
                                                            statistics and           alpha (Google);
                                                            comments.                scraping

     Sign-in                        Google OAuth only,      The same consent         Hosted auth services,
                                    sessions stored in      screen connects the      password login
                                    Postgres                YouTube channel. No
                                                            passwords are stored.

     Live updates                   Server-Sent Events      Enough for remote        A WebSocket layer
                                                            and dashboard status.

     Deployment                     Docker Compose on       One command starts       Kubernetes
                                    one Linux server,       everything.
                                    Caddy for HTTPS

     Secrets                        Environment variables   Nothing sensitive in     Keys in code or
                                    injected at deploy.     the repository or in     settings files
                                    OAuth refresh tokens    config files.
                                    encrypted in the
                                    database.

     Tests                          pytest and Playwright   The acceptance tests     Manual testing only
                                                            are what the agents
                                                            build against.


  The gamer needs a computer running OBS and one of two capture routes.

         Capture card, with HDCP turned off on the PS5. Best quality.
         PS Remote Play into OBS, with no capture card. Sony supports it, and quality is lower
         (OneStream guide).

  The PS5's own broadcast button cannot be used. It streams only to Twitch or YouTube, one
  at a time (Elgato).

  A 6 Mbps stream is about 2.7 GB per hour coming in and the same going out to YouTube.
  Size the server's bandwidth on that figure times your concurrent streams.




                                                                                                        Page 7 of 16
Clipdesk Missions: product design document




  Mission engine
  The engine runs once a day for the whole platform and turns public questions into a
  ranked pool of mission cards.

     1. Collect. Search YouTube for GTA 6 uploads from the last 48 hours, sorted by views.
        Pull statistics for each video and the top comments on the best ones.
     2. Extract questions. The model reads titles and comments and lists the questions
        people ask, such as "can you", "what happens if" and "is it possible".
     3. Merge duplicates. Similar questions become one, with a count of how many people
        asked.
     4. Score. Rank each question with the formula below.
     5. Write cards. The model turns the top questions into mission cards in a fixed JSON
        format.
     6. Check policy. Automatic rules remove story spoilers, online cheats and unsafe titles.
     7. Editor pass. A person on your team approves the pool in the admin page. This takes
        minutes and keeps quality high.

  The score multiplies four factors and subtracts one.


     Factor                              Meaning                                 Source

     Demand                              How many people asked, and views        YouTube Data API
                                         on related videos

     Outlier strength                    Views of related videos against the     YouTube Data API
                                         size of the channels that posted them

     Feasibility                         Playable in free roam in under ten      Model estimate, then real
                                         minutes                                 completions

     Track record                        How earlier missions of the same type   Your own results table
                                         performed on the platform

     Saturation,                         How many videos already answer the      YouTube Data API
     subtracted                          question


  Each mission card has this shape.




                                                                                                             Page 8 of 16
Clipdesk Missions: product design document




     {
         "id": "m_0214",
         "question": "Can you outrun five stars on a bicycle?",
         "hook_text": "5 STARS. ONE BICYCLE.",
         "setup": "Get five stars downtown, then switch to any bicycle.",
         "win_condition": "Lose the wanted level without leaving the bike.",
         "result_type": "time_seconds",
         "est_minutes": 8,
         "title_options": ["Can you escape 5 stars on a BIKE in GTA 6?"],
         "mode": "free_roam",
         "status": "unverified",
         "evidence": {"askers": 0, "source_video_ids": []},
         "policy": {"spoiler": false, "online_exploit": false}
     }


  Three rules are specific to launch week.

         Missions start as unverified. Nobody knows yet what the game allows. A mission
         becomes verified when one creator completes it.
         A failure is still a Short. "It turns out you can't" answers the question too.
         v0 skips steps 1 to 3. Your team types 20 to 30 questions by hand, and the model
         writes the cards.

  Search calls are the expensive part of the YouTube quota, so the engine runs them once
  centrally and never per user. Confirm the current cost per call in your Cloud Console.


  Clip engine
  The engine receives a mission and two timestamps and returns one finished Short. It
  never has to decide whether a moment is worth clipping.

     1. Fetch the window. Take recording segments from 10 seconds before Start to 5
        seconds after Done. Join them without re-encoding.
     2. Transcribe. Run faster-whisper on that window for word-level timing.
     3. Pick the beats. The payoff is the last 15 to 20 seconds before Done. The setup is two
        or three short pieces chosen by voice energy and by the model reading the transcript.
        The total stays under 45 seconds.
     4. Build the hook. The first two seconds show the mission's hook text over the strongest
        frame from the payoff.
     5. Lay out. Convert to 9:16 with one layout from a rotating set.



                                                                                            Page 9 of 16
Clipdesk Missions: product design document




     6. Caption. Burn in word-highlighted captions.
     7. End card. Show the result, the mission number and the leaderboard rank.
     8. Render. Output 1080 by 1920 H.264 with a thumbnail.
     9. Write metadata. Title from the mission's options, description with the live link, tags.

  Four rules keep the output safe and distinct.

         Speed target: the Short is ready about two minutes after Done. Measure this in
         rehearsal; it is a goal, not a tested figure.
         Variation: layouts, caption styles and music beds rotate, so no two consecutive Shorts
         share a template.
         Spoiler guard: a window with no speech and no interface on screen is treated as a
         cutscene and dropped.
         Missed taps: the voice phrase closes a mission, and ending the stream closes any
         mission still open.

  The relay carries one mixed audio track. Voice and game sound are not separated in this
  design, so loudness signals are weaker than in the earlier local plan.


  Data model and API
  Thirteen tables hold all state. The API contract lives in one OpenAPI file that both the web
  app and the agents build against.


     Table                         Holds                         Key fields

      users                        One row per person            Google subject id, display name, role

      channels                     Connected YouTube channels    user, YouTube channel id, title

      oauth_tokens                 Encrypted refresh tokens      channel, ciphertext, scopes

      missions                     The mission cards             card JSON, score, status, type

      daily_sets                   Which missions run on which   date, daily mission, pool
                                   date

      assignments                  A mission accepted by a       user, mission, date, state
                                   creator

      streams                      One live session              user, stream key hash, start, end, storage
                                                                 prefix



                                                                                                         Page 10 of 16
Clipdesk Missions: product design document




     Table                         Holds                        Key fields

      marks                        Start and Done taps          assignment, stream, kind, stream time,
                                                                result

      clips                        Rendered Shorts              assignment, file key, title, state, template

      posts                        Published copies             clip, platform, remote id, time

      metrics                      Results per post             post, views, average view percentage,
                                                                read time

      attempts                     Leaderboard entries          mission, user, result value, clip

      templates                    Layout and caption presets   JSON, weight


  The job queue adds its own tables. Votes get a table in v2.


     Area                    Endpoint                                    Purpose

     Sign-in                  GET /auth/google/start , GET               Session and channel connect
                             /auth/google/callback , GET /me

     Missions                 GET /today , POST /assignments , POST      Today page
                             /assignments/{id}/swap

     Streaming                POST /streams , POST                       Issue a stream key; relay
                             /hooks/relay/auth , POST                    callbacks
                             /hooks/relay/ready , POST
                             /hooks/relay/ended

     Remote                   POST /marks , GET /events                  Start and Done; live status over
                                                                         Server-Sent Events

     Clips                    GET /clips , PATCH /clips/{id} , POST      Review and publish
                             /clips/{id}/approve , POST
                             /clips/{id}/post

     Community                GET /m/{slug} , GET                        Public mission page and ranking
                             /missions/{id}/leaderboard

     Admin                    GET /admin/pool , POST                     Editor pass and typed questions
                             /admin/pool/{id}/approve , POST
                             /admin/questions




                                                                                                       Page 11 of 16
Clipdesk Missions: product design document




  The relay hooks accept calls only from the relay's own address and a shared secret read
  from the environment.


  Community and business model
  The community forms around the Daily Mission, and the business charges for volume and
  automation while the missions themselves stay free.

  Five mechanics build the community.

         Daily Mission. The same challenge for everyone, new each day.
         Leaderboard. Every attempt is ranked by its result. Creators come back to beat each
         other.
         Public mission pages. One page per mission shows every attempt as an embedded
         Short. These pages are searchable and link viewers to all participating channels.
         Mission number on every Short. A small, consistent mark such as "Mission 214" on
         the end card. It makes the series recognisable across channels and is the platform's
         advertising.
         Creator-submitted missions. From v2, creators propose missions and get credit
         when theirs is chosen.


     Plan        Includes                                    Purpose

     Free        Daily Mission, leaderboard entry, a small   Fills the leaderboards and spreads the
                 number of clips per stream                  mission mark

     Paid        Personal mission picks, unlimited clips,    Revenue
                 approve-and-post, chat votes, bonus
                 moments


  Set the price after about 20 outside creators have used v1. Competing clip tools charge
  roughly $9 to $29 a month, which frames what streamers expect to pay.

  Four limits apply before selling.

         Upload quota is shared. The YouTube reference page lists 100 upload calls a day per
         API project. That covers every creator on the platform together until Google grants
         more.
         Google verification. The upload permission needs Google's OAuth review before
         strangers can connect channels.



                                                                                                 Page 12 of 16
Clipdesk Missions: product design document




         Trademarks. Do not put GTA or Rockstar in the product name, and do not imply
         endorsement. Build the mission format to work for any open-world game.
         Hardware. Each customer needs a computer with OBS. A PS5 alone is not enough,
         which narrows the market.

  Revenue cannot be forecast from this design. Your own channel is the first proof. If
  mission Shorts outperform ordinary clips there, that result is the sales pitch.


  Build plan for AI agents
  Split the work into packages that touch separate folders, give each one an acceptance
  test, and let agents run them in parallel.

  Four working rules.

         One repository. Folders: web/ , api/ , worker/ , relay/ , contracts/ , docs/ .
         Contracts first. contracts/openapi.yaml and the mission card JSON schema are
         written before any code. Agents may not change them without a human approving.
         The test is the definition of done. An agent's package is finished when its acceptance
         test passes in CI.
         A person reviews every merge. Generated code goes through review and your
         security checks before it reaches the main branch.


     Package            Deliverable                      Needs     Acceptance test                Cut

     WP0                Repository, Docker Compose       Nothing   docker compose up passes       v0
                        with Postgres, API, web, relay             every health check
                        and worker, CI

     WP1                Relay: stream-key check,         WP0       A 10-minute OBS test stream    v0
                        recording to storage, forward              appears on an unlisted
                        to YouTube                                 YouTube broadcast and as
                                                                   segments in storage

     WP2                Mission writer, Today page,      WP0       Ten typed questions return     v0
                        admin pool page                            ten cards that pass the
                                                                   JSON schema

     WP3                Phone remote with Start and      WP1,      Marks are stored with          v0
                        Done                             WP2       stream time accurate to one
                                                                   second




                                                                                                 Page 13 of 16
Clipdesk Missions: product design document




     Package            Deliverable                     Needs   Acceptance test                 Cut

     WP4                Clip worker, reusing            WP1     A fixture recording plus two    v0
                        Clipdesk's render code                  marks yields a 1080 by 1920
                                                                file under 60 seconds with
                                                                captions

     WP5                Clips page: preview, retitle,   WP4     Playwright test approves a      v0
                        approve, download                       clip and downloads it

     WP6                Google sign-in, channel         WP0     A second test account sees      v1
                        connect, token encryption               only its own data

     WP7                Question miner on the           WP2     A run stores at least 20        v1
                        YouTube Data API                        merged questions with
                                                                counts

     WP8                Post to YouTube with            WP5,    An approved clip appears on     v1
                        schedule                        WP6     the test channel as unlisted

     WP9                Leaderboards and public         WP3     Two attempts on one mission     v1
                        mission pages                           rank correctly on the public
                                                                page

     WP10               Results collector and mission   WP8     Metrics for a test post are     v1
                        scoring                                 stored and change that
                                                                mission's score


  A workable two-day order for v0.

     1. Day 1 morning: WP0, then write the contracts.
     2. Day 1 afternoon: WP1, WP2 and WP4 in parallel.
     3. Day 2 morning: WP3 and WP5.
     4. Day 2 afternoon: full rehearsal on GTA 5. One real stream, three missions, three
        Shorts.

  Keep a fallback for launch day. If the relay is not stable by the rehearsal, stream straight to
  YouTube, record locally in OBS, and upload the file to the clip worker with the mission
  times typed in. The missions and the Shorts still work.


  Risks, unverified assumptions and sources
  The relay and the deadline are the two risks most likely to hurt launch day.



                                                                                               Page 14 of 16
Clipdesk Missions: product design document




     Risk                                    Effect                  What reduces it

     The relay fails mid-stream              The live stream drops   Keep the relay as a pass-
                                                                     through with no re-encoding.
                                                                     Save YouTube's direct address
                                                                     as a second OBS profile for a
                                                                     one-click switch.

     Two days is not enough for v0           No platform on launch   The fallback path in the build
                                             day                     plan. Missions can be run from
                                                                     a shared page alone.

     The format is copied                    The idea stops being    Move fast on v1. The
                                             unique                  leaderboards and pooled
                                                                     results are the part that is hard
                                                                     to copy.

     The same mission across                 Monetisation risk for   Each creator's own voice and
     many channels looks                     creators                gameplay, rotating layouts, a
     templated to YouTube                                            human approval step. Watch
                                                                     this closely in v1.

     Take-Two removes or claims              Lost Shorts             Free-roam missions only, no
     videos                                                          cutscenes, no plot words in
                                                                     titles.

     Upload quota is shared across           Posting stops for       Ask Google for more quota
     all users                               everyone at the cap     during v1. Offer download-and-
                                                                     post as the fallback.

     Costs grow with every                   Margins unknown         Measure bandwidth, storage
     concurrent stream                                               and model cost per stream
                                                                     hour in v1 before setting a
                                                                     price.


  Not verified in this session. The agents must check current documentation before
  building on these.

         Procrastinate as the Postgres job library, and Authlib for Google sign-in.
         faster-whisper speed on a CPU for mission windows.
         The exact MediaMTX configuration for per-user stream keys with forwarding to each
         user's own YouTube key.




                                                                                                 Page 15 of 16
Clipdesk Missions: product design document




         YouTube Data API quota costs for search calls.
         Delay added to the live stream by the relay.
         Nothing in this document was built or tested. Clipdesk's code was not available here,
         only your summary of it.

  Sources opened or read as search extracts today.

         MediaMTX repository and a 2026 RTMP server comparison
         Gemini video understanding documentation
         Google's Trends API announcement
         Elgato on streaming directly from a PS5
         YouTube Data API: videos.insert
         The earlier Clipdesk platform plan holds the policy and competitor research this
         design relies on.




                                                                                            Page 16 of 16

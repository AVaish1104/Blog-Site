"""Sample articles used by `seed_demo`. Clearly marked as demo content wherever shown."""

AUTHOR = {
    "name": "Iris Calloway",
    "slug": "iris-calloway",
    "bio": (
        "A sample author profile created by the setup script. Replace it with your own "
        "profile in the studio, or remove all demo content with the seed_demo --clear command."
    ),
}

CATEGORIES = [
    ("Writing", "writing", "On sentences, drafts, and the slow work of saying things clearly."),
    ("Design", "design", "Typography, layout, and the small decisions that make things usable."),
    ("Technology", "technology", "Tools, the web, and building software that lasts."),
    ("Notes", "notes", "Shorter observations and works in progress."),
]

# (title, category slug, tags, excerpt, body, days_ago, featured)
POSTS = [
    (
        "Editing is mostly subtraction",
        "writing",
        ["Editing", "Craft"],
        "The first draft is for finding out what you think. Every draft after that is for "
        "removing what gets in the way.",
        """The first draft is where you discover what you are trying to say. It is allowed to be long, repetitive and wrong. Its only job is to exist.

Editing is a different activity entirely. Most of the time, it means taking things away.

## What to cut first

Start with the sentences that announce what you are about to say. *In this essay I will argue* can almost always go. So can the paragraph that restates the one before it, and the qualifier that protects you rather than informs the reader.

- Throat-clearing openings
- Sentences that summarise the previous paragraph
- Adverbs doing the work a better verb should do
- Hedges that exist only to avoid being wrong

## Keep the strange parts

Subtraction is not the same as flattening. The detail that only you would notice is often the reason the piece is worth reading. Cut the scaffolding, not the view.

> A good edit leaves the writer's voice louder, not quieter.

When a draft feels finished, try removing ten percent of it. You will rarely miss what is gone.""",
        6,
        True,
    ),
    (
        "Typography is interface",
        "design",
        ["Typography", "Reading"],
        "Before anyone clicks anything, the type has already told them how to read the page.",
        """We tend to talk about interface as the things people press: buttons, menus, links. But on a page made mostly of words, the type *is* the interface.

## Hierarchy is navigation

A reader scanning an article uses size, weight and space to decide where to look. A clear hierarchy lets them find the argument without reading every line. A muddled one forces them to.

Three levels are usually enough: a title, a few section headings, and body text. More than that and the levels stop being distinguishable.

## Measure matters more than font

The single most effective typographic decision is often line length. Around 60 to 75 characters per line is comfortable for long reading. Wider than that and the eye loses its place returning to the start of the next line.

## Contrast is not optional

Light grey text on white looks refined in a mockup and is unreadable on a sunny afternoon. Body text should be close to black. Save the softer tones for metadata that genuinely matters less.

Good typography rarely draws attention to itself. It simply makes reading feel easier than it should.""",
        13,
        False,
    ),
    (
        "The quiet usefulness of RSS",
        "technology",
        ["Web", "RSS", "Reading"],
        "A twenty-year-old format still does something most modern platforms won't: it lets "
        "readers choose what they follow, on their own terms.",
        """RSS is not exciting. It is a list of recent items in a predictable format, fetched by a program of the reader's choosing. That is exactly why it has lasted.

## What it gets right

A feed has no algorithm. Items arrive in the order they were published, and nothing is promoted because it performs well. If a reader subscribes to a site, they see everything it publishes — no more, no less.

It is also portable. Readers can move their subscriptions from one app to another by exporting a single file.

## Publishing one costs almost nothing

For a blog, a feed is a byproduct of data you already have: titles, summaries, dates and links. This site publishes both RSS and Atom versions at stable addresses, linked from every page's header so feed readers can discover them automatically.

```
/feed/       RSS 2.0
/feed/atom/  Atom 1.0
```

If you run a site, publish a feed. Some of your most attentive readers are using one.""",
        20,
        False,
    ),
    (
        "What a grid is for",
        "design",
        ["Layout", "Grids"],
        "A grid is not a cage. It is a set of decisions made once, so you don't have to make "
        "them again on every page.",
        """People sometimes describe grids as restrictive. In practice they are the opposite: a grid removes a whole category of small, arbitrary decisions.

## Alignment creates calm

When elements share edges, the page reads as organised even if the content is varied. When every block sits at its own slightly different offset, the result feels busy no matter how little is on it.

## Fewer columns than you think

A twelve-column grid is flexible, but most pages only need two or three meaningful divisions. A wide column for reading, a narrow one for supporting detail, and generous margins.

1. Decide the reading width first.
2. Let everything else align to it or to the page edge.
3. Use space, not lines, to separate groups.

## Break it deliberately

A grid makes exceptions visible. A full-width image or an outdented quote means something precisely because everything else lines up. Without the grid, there is nothing to break.""",
        27,
        False,
    ),
    (
        "Reading slowly on purpose",
        "notes",
        ["Reading", "Attention"],
        "Not everything should be skimmed. Some writing only works if you give it the time it "
        "asks for.",
        """Most of what we read online is designed to be scanned. Headlines, bullet points, bolded phrases: all useful, all optimised for speed.

But some writing rewards the opposite. An essay that builds an argument slowly, or a story that depends on rhythm, falls apart when skimmed.

## A few habits that help

- Read long pieces in a single sitting rather than across tabs
- Read on paper or in a reader mode when possible
- Stop at the end of a section and summarise it to yourself
- Accept that you will read fewer things

Slow reading is not a productivity technique. It is closer to the opposite: a decision that some things are worth more time than they strictly require.""",
        34,
        False,
    ),
    (
        "Good defaults are a form of respect",
        "design",
        ["Defaults", "Usability"],
        "Most people never change a setting. Whatever you choose as the default is, for them, "
        "simply how the thing works.",
        """Every product has defaults, whether or not anyone chose them deliberately. And because most people never open the settings, those defaults decide the experience for nearly everyone.

## Choose for the person who won't customise

Design the default for someone in a hurry who will never visit the preferences page. If the default requires configuration to be pleasant, it is the wrong default.

## Make the safe choice the easy one

Destructive actions should require confirmation. Privacy-preserving options should be on unless there is a good reason otherwise. Data should be saved before it can be lost.

> Settings are where designers hide decisions they didn't want to make.

## Defaults change behaviour

People treat defaults as recommendations. If comments are pre-moderated by default, communities tend to be calmer. If a newsletter form asks for explicit consent, the resulting list is smaller and far more engaged.

A good default is a decision made carefully on behalf of someone who trusts you to have made it.""",
        41,
        False,
    ),
    (
        "Why the web should be fast",
        "technology",
        ["Performance", "Web"],
        "Speed is not a feature you add at the end. It is a consequence of everything you "
        "decided not to include.",
        """A fast page is mostly the result of restraint. Fewer scripts, fewer fonts, fewer requests, smaller images. Each individual addition seems harmless; together they add seconds.

## Where the time goes

On a typical article page, the text itself is a tiny fraction of the bytes delivered. The rest is tracking scripts, advertising, oversized images and fonts in weights that never appear.

## A simple budget

This site renders pages on the server, sends a single stylesheet, self-hosts two font files, and ships only a few kilobytes of JavaScript — enough to toggle a menu on small screens. Everything works without it.

- Images are resized on upload and lazy-loaded below the fold
- Fonts are subset and preloaded
- No third-party scripts

## Speed is accessibility

Not everyone has a new phone and fast connection. A light page is the difference between being readable and not for a meaningful number of people.""",
        48,
        False,
    ),
    (
        "Notes on maintenance",
        "technology",
        ["Maintenance", "Craft"],
        "Building something is a moment. Maintaining it is most of its life.",
        """We celebrate launches. Maintenance gets less attention, though it is where most of the work happens and where most of the value is preserved.

## Choose boring foundations

Well-established tools have known failure modes, documentation, and people who have already solved your problem. Novelty is expensive to maintain.

## Write things down

The person who maintains a project in two years may be you, and you will have forgotten why you made half the decisions. A short README section explaining *why* is worth more than pages explaining *what*.

## Make updates small and frequent

Dependencies left untouched for years become a migration project. Updated a little at a time, they remain routine.

Maintenance is unglamorous. It is also the difference between something that lasts and something that merely launched.""",
        55,
        False,
    ),
    (
        "Designing for the second visit",
        "design",
        ["Usability", "Navigation"],
        "First impressions matter, but most of a site's value comes from people who return.",
        """A great deal of design effort goes into the first visit: the hero image, the introduction, the onboarding. But readers who come back behave differently.

## Returning readers want the new thing

Someone visiting for the tenth time knows what the site is. They want to see what has changed. Put the most recent writing where they can find it immediately.

## Stable locations build habits

Navigation that stays in the same place, URLs that don't change, and a predictable structure all let regular readers move quickly. Redesigns that move everything have a cost that doesn't show up in screenshots.

## Offer ways to keep in touch

Feeds and newsletters let interested readers return without remembering to. Make them easy to find, and make leaving them just as easy.""",
        62,
        False,
    ),
    (
        "Short sentences, long thoughts",
        "writing",
        ["Craft", "Style"],
        "Clarity at the sentence level makes room for complexity at the level of ideas.",
        """There is a misconception that serious ideas require complicated sentences. Usually the reverse is true.

When each sentence carries one clear thought, the reader's attention is free to follow the argument. When sentences are tangled, readers spend their effort parsing grammar instead.

## Vary the rhythm

Short sentences are not a rule. A paragraph of nothing but short sentences reads like a list of telegrams. Use length for effect. Let a longer sentence carry a complicated relationship between ideas, then follow it with a short one. Like this.

## Read it aloud

The fastest way to find a sentence that doesn't work is to say it out loud. If you run out of breath, or have to restart, the reader will stumble too.""",
        76,
        False,
    ),
    (
        "In praise of plain text",
        "notes",
        ["Tools", "Writing"],
        "Files you can open in any editor, on any computer, decades from now.",
        """Every few years a new note-taking app promises to change how we think. Many of them are good. Some of them disappear, taking their proprietary formats with them.

Plain text doesn't disappear. A Markdown file written today will open on whatever computer exists in thirty years.

## What you give up

Rich formatting, embedded media, real-time collaboration. For a lot of writing, these matter less than they appear to.

## What you keep

Portability, searchability, version control, and the ability to switch tools without converting anything. This site stores every article body as Markdown for exactly that reason.""",
        90,
        False,
    ),
    (
        "Consent is a design decision",
        "notes",
        ["Privacy", "Defaults"],
        "How a form asks for permission says a lot about how the people behind it think about "
        "their readers.",
        """A newsletter form can be designed to maximise sign-ups or to respect the people signing up. Those aren't always the same thing.

## Say exactly what will happen

The consent text next to a sign-up form should describe what the reader is agreeing to in plain language: what they'll receive, roughly how often, and how to stop.

## Confirm before you send

Double opt-in — asking new subscribers to click a link in a confirmation email — prevents people from being signed up by someone else and keeps the list honest.

## Make leaving easy

Every email should carry a working unsubscribe link that takes one click. A reader who can leave easily is far more willing to stay.""",
        104,
        False,
    ),
]

SCHEDULED_POST = (
    "A note on what comes next",
    "notes",
    ["Updates"],
    "A short scheduled post, demonstrating how future-dated articles stay hidden until their "
    "publication time.",
    """This post was created by the setup script with a publication date in the future. Until that moment arrives it is listed as *Scheduled* in the studio and does not appear anywhere on the public site, in feeds, in search, or in the sitemap.

When its time comes it becomes visible automatically — no background job is needed, because visibility is decided each time a page is requested.""",
    -3,
)

DRAFT_POST = (
    "Unfinished: a draft in progress",
    "writing",
    ["Drafts"],
    "",
    """This is a demo draft. Drafts are only visible in the studio. Open it in the editor to try the Markdown toolbar, the preview, and publishing.""",
)

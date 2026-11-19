# Real user questions: FlutterFix

Written the way my user types them.

**User:** Mobile developer at a Coimbatore agency maintaining a Flutter 2 app for a textile shop that must move to the latest Flutter to meet a Play Store target-SDK deadline.

These 10 questions become my first evaluation set in Week 3. Question 6 is not answerable from my documents: the product must say "I don't know".

| # | Question | Type | Where the answer is (document, page) | More than one page? |
|---|---|---|---|---|
| 1 | What is the difference between StatelessWidget and StatefulWidget? | simple | Flutter docs — StatelessWidget and StatefulWidget class documentation | No |
| 2 | What does sound null safety mean in Dart? | simple | Dart docs — Sound null safety guide | No |
| 3 | What changed when Material 3 became the default in Flutter? | simple | Flutter breaking changes — Material 3 default in Flutter 3.16 | Yes |
| 4 | Our Flutter 2.10 app uses FlatButton, RaisedButton, WillPopScope and packages without null safety. List every change needed to build on the latest stable Flutter, in the right order, with the breaking-change pages. | multi-step (several pages) | Flutter breaking changes — Deprecated buttons, WillPopScope to PopScope, Null Safety migration guide | Yes |
| 5 | Compare Provider and Riverpod for app-wide state. | comparison | Flutter docs — Simple app state management; Riverpod documentation | Yes |
| 6 | Why does our app crash on the shop owner's phone? | unanswerable: must reply "I don't know" | none: not in any document | - |
| 7 | How do I migrate Scaffold.showSnackBar to ScaffoldMessenger in Flutter 3? | simple | Flutter breaking changes — ScaffoldMessenger migration guide | No |
| 8 | How do I replace the deprecated ButtonTheme and accentColor in my ThemeData? | simple | Flutter breaking changes — ThemeData deprecations | Yes |
| 9 | If our pubspec specifies flutter: ">=2.10.0 <3.0.0", how should we update the SDK constraints for Flutter 3.x? | simple | Flutter docs — Flutter SDK releases and Dart version constraints | No |
| 10 | What should we check before replacing WillPopScope with PopScope in Android 14? | multi-step | Flutter breaking changes — Android predictive back and WillPopScope deprecation | Yes |

## Source references

1. Flutter Breaking Changes: https://docs.flutter.dev/release/breaking-changes
2. Flutter Official Documentation: https://docs.flutter.dev/
3. Dart Language Documentation: https://dart.dev/
4. Flutter Website Repository: https://github.com/flutter/website
5. Flutter Deprecated Buttons Guide: https://docs.flutter.dev/release/breaking-changes/buttons
6. Flutter Android 14 / Target SDK Migration Guide: https://docs.flutter.dev/release/breaking-changes/android-target-sdk-34
7. Flutter PopScope Migration Guide: https://docs.flutter.dev/release/breaking-changes/will-pop-scope-deprecated
8. Dart Null Safety Guide: https://dart.dev/null-safety
9. Flutter Material 3 Guide: https://docs.flutter.dev/ui/design/material

**Note:** These references identify the relevant breaking-change documents and sections. The actual answers and migration verdicts must be validated with the Dart Analysis Server on the target SDK before presenting to the user.

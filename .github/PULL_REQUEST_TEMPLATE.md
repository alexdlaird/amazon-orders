**Description**
A clear and concise description of what was changed.

**Issues**
A list of GitHub issues related to this PR.

**Type of Change**
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update

**Testing Done**
A clear and concise description of the new tests added to validate the change as well as any manual testing done.

Note that for the PR to be considered for merging, if you are adding a new page to the auth flow or a new field to an
entity, there _must_ be a test, and that test _must_ reference an HTML file in ``tests/resources``. All changes must
be _additive_, meaning your change can't cause regressions in previous parsing code (as another user might still be
seeing that page in their account).

**Checklist**
- [ ] My code follows the PEP 8 style guidelines for Python
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code in particularly hard-to-understand areas
- [ ] If applicable, I have made corresponding changes to the documentation
- [ ] I have added tests that prove my change is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] My changes generate no new warnings

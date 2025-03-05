module.exports = {
    extends: ['eslint'],
    rules:{
        'subject-case': [2,'never', ['lower-case','sentence-case']],
        'subject-empty': [0,'never'],
        'type-empty': [0, 'never'],
        'type-case': [2, 'always', 'sentence-case'],
        'subject-full-stop': [0,'never'],
        'type-enum': [2,'always', ['Fix', 'New', 'Update', 'Breaking', 'Docs','RELEASE']]
    },
//    ignores: [(commit) => commit.includes('RELEASE')],
};
// Level [0..2]: 0 disables the rule. For 1 it will be considered a warning for 2 an error
// Problem: We have commits without structure type scope subject see: https://blog.greenkeeper.io/introduction-to-semantic-release-33f73b117c8
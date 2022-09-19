export async function loadData() {
    return [
        [1, 2, 3],
        ["1", "2", "3"],
        [0.1, 0.2, 0.3],
        ["0.1", "0.2", "0.3"],
        ['', null, undefined],
        [new Date(2021, 8, 1), new Date(2021, 8, 2), new Date(2021, 8, 3)],
    ];
}
import pytest
from docker_cookiecutter import pathmap


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param(["a"], ["a"], id="single - relative - trivial"),
        pytest.param(["/"], ["/"], id="single - root - linux"),
        pytest.param(["/a"], ["/a"], id="single - absolute - linux"),
        pytest.param(["c:\\"], ["c:\\"], id="single - root - windows"),
        pytest.param(["c:\\a"], ["c:\\a"], id="single - absolute - windows"),
        pytest.param(["a", "b"], ["a", "b"], id="multi - no overlap"),
        pytest.param(["a", "a/b"], ["a"], id="multi - mounting both parent and child"),
        pytest.param(
            ["a", "a/b/c"], ["a"], id="multi - mounting both parent and indirect child"
        ),
        pytest.param(
            ["a/b", "a"],
            ["a"],
            id="multi - mounting both parent and child - out of order",
        ),
    ],
)
def test_reduce_mounts(given, want):
    result = pathmap.reduce_mounts(given)
    assert set(result) == set(want)


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param("a", "a", id="trivial"),
        pytest.param("a/", "a", id="trailing - linux"),
        pytest.param("a\\", "a", id="trailing - windows"),
        pytest.param("/", "/", id="root - linux"),
        pytest.param("///", "/", id="root - repeated - linux"),
        pytest.param("c:\\", "c:\\", id="root - windows"),
        pytest.param("c:\\\\\\", "c:\\", id="root - repeated - windows"),
        pytest.param("a/b", "a/b", id="inner - trivial - linux"),
        pytest.param("a///b", "a/b", id="inner - repeated - linux"),
    ],
)
def test_normalize_path(given, want):
    result = pathmap.normalize_path(given)
    assert result == want


@pytest.mark.parametrize(
    "given,want_parent,want_child",
    [
        pytest.param("a", None, "a", id="trivial - relative"),
        pytest.param("/", None, "/", id="trivial - absolute - root - linux"),
        pytest.param("c:\\", None, "c:\\", id="trivial - absolute - root - windows"),
        pytest.param("/a", "/", "a", id="trivial - absolute - one level"),
        pytest.param("/a/b/c", "/a/b", "c", id="absolute - multi level"),
        pytest.param(
            "c:\\a\\b\\c", "c:\\a\\b", "c", id="absolute - multi level - windows"
        ),
        pytest.param(
            "/a/b/c/", "/a/b", "c", id="absolute - multi level - trailing slash"
        ),
        pytest.param(
            "c:\\a\\b\\c\\",
            "c:\\a\\b",
            "c",
            id="absolute - multi level - trailing slash - windows",
        ),
    ],
)
def test_parse_parent_child(given, want_parent, want_child):
    result_parent, result_child = pathmap.parse_parent_child(given)
    assert (result_parent, result_child) == (want_parent, want_child)


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param("a", "a", id="trivial"),
        pytest.param("a/", "a", id="trailing - linux"),
        pytest.param("a\\", "a", id="trailing - windows"),
        pytest.param("/", "/", id="root - linux"),
        pytest.param("///", "/", id="root - repeated - linux"),
        pytest.param("c:\\", "/", id="root - windows"),
        pytest.param("c:\\\\\\", "/", id="root - repeated - windows"),
        pytest.param("a/b", "a/b", id="inner - trivial - linux"),
        pytest.param("a///b", "a/b", id="inner - repeated - linux"),
    ],
)
def test_transform_to_nix_path(given, want):
    result = pathmap.transform_to_nix_path(given)
    assert result == want


@pytest.mark.parametrize(
    "given_paths,want_mappings",
    [
        pytest.param(["/a"], {"/a": "/h/abs/a"}, id="absolute - trivial"),
        pytest.param(["a"], {"a": "/h/rel/a"}, id="relative - trivial"),
        pytest.param(
            ["/a/b/", "/c", "c:\\d"],
            {
                "/a/b/": "/h/abs/a/b",
                "/c": "/h/abs/c",
                "c:\\d": "/h/abs/d",
            },
            id="absolute - multiple - mix linux and win",
        ),
    ],
)
def test_map_host_to_container_jiggy(given_paths, want_mappings):
    # given
    sut = pathmap.PathMap(given_paths, container_abs="/h/abs", container_rel="/h/rel")

    # when
    mounts = sut.get_mounts()
    result_mappings = {
        host_path: sut.get_container_path(host_path)
        for host_path in want_mappings.keys()
    }

    # then
    for mount_host in mounts:
        mount_container = sut.get_container_path(mount_host)
        assert (
            len(mount_container.strip()) > 0
        ), "reduced mount should have a non-empty mapping"
        assert (
            mount_host != mount_container
        ), "reduced mount should be mapped to container path"

    assert result_mappings == want_mappings

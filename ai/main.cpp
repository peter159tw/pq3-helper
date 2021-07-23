#include <iostream>
#include <array>
#include <map>
#include <string>
#include <vector>
#include <optional>
#include <unordered_set>

class GridParser
{
public:
    GridParser()
    {
        _grid_chars = "BGPRSY";
    }

    int parse(const char c) const
    {
        const int r = _grid_chars.find_first_of(c);
        if (r == std::string::npos)
            return -1;
        return r;
    }

    char to_string(int v) const
    {
        if (v < 0 || v >= _grid_chars.size())
            return '?';
        return _grid_chars[v];
    }

private:
    std::string _grid_chars;
};

using PointT = std::pair<int, int>;

template <class ValueT>
using BoardArrayT = std::array<std::array<ValueT, 5>, 7>;

namespace std
{
    template <>
    class hash<BoardArrayT<int>>
    {
    public:
        std::size_t operator()(const BoardArrayT<int> &obj) const
        {
            std::size_t v = 0;
            for (const auto &row : obj)
            {
                for (const auto &item : row)
                {
                    hash_combine(v, item);
                }
            }
            return v;
        }

    private:
        void hash_combine(std::size_t &seed, int v) const
        {
            seed ^= v + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        }
    };
}

class Board
{
public:
    void parse(const std::string_view s, const GridParser &grid_parser)
    {
        int s_idx = 0;
        for (int y = 0; y < 5; ++y)
        {
            for (int x = 0; x < 7; ++x)
            {
                grids_[x][y] = grid_parser.parse(s[s_idx]);
                locked_[x][y] = false;
                s_idx++;
            }
        }
    }

    void print(const GridParser &grid_parser) const
    {
        for (int y = 0; y < 5; ++y)
        {
            for (int x = 0; x < 7; ++x)
            {
                std::cout << grid_parser.to_string(grids_[x][y]);
                std::cout << (locked_[x][y] ? '*' : ' ');
                std::cout << ' ';
            }
            std::cout << std::endl;
        }
    }

    bool in_range(int x, int y) const
    {
        return x >= 0 && x < 7 && y >= 0 && y < 5;
    }

    Board make_copy() const
    {
        Board ret;
        ret.grids_ = grids_;
        ret.locked_ = locked_;
        return ret;
    }

    void update_locks();

    std::optional<Board> swap(int x1, int y1, int x2, int y2) const;

    BoardArrayT<int> grids_;
    BoardArrayT<bool> locked_;
};

class MatchThreeChecker
{
public:
    MatchThreeChecker(Board &board) : board_(board), candidates_(), candidates_v_(0) {}

    void add(int x, int y)
    {
        int v = board_.grids_[x][y];
        if (!candidates_.empty() && candidates_v_ != v)
        {
            mark_locks();
            candidates_.clear();
        }
        candidates_v_ = v;
        candidates_.push_back(PointT(x, y));
    }

    void mark_locks()
    {
        if (candidates_.size() < 3)
            return;
        for (const PointT &pnt : candidates_)
        {
            board_.locked_[pnt.first][pnt.second] = true;
        }
    }

private:
    Board &board_;
    std::vector<PointT> candidates_;
    int candidates_v_;
};

void Board::update_locks()
{
    for (int x = 0; x < 7; ++x)
    {
        MatchThreeChecker checker(*this);
        for (int y = 0; y < 5; ++y)
        {
            checker.add(x, y);
        }
        checker.mark_locks();
    }

    for (int y = 0; y < 5; ++y)
    {
        MatchThreeChecker checker(*this);
        for (int x = 0; x < 7; ++x)
        {
            checker.add(x, y);
        }
        checker.mark_locks();
    }
}

std::optional<Board> Board::swap(int x1, int y1, int x2, int y2) const
{
    if (!in_range(x1, y1))
        return std::nullopt;
    if (!in_range(x2, y2))
        return std::nullopt;

    if (locked_[x1][y1] || locked_[x2][y2])
        return std::nullopt;

    Board ret = this->make_copy();
    std::swap(ret.grids_[x1][y1], ret.grids_[x2][y2]);

    ret.update_locks();
    if (!ret.locked_[x1][y1] && !ret.locked_[x2][y2])
    {
        return std::nullopt; // not swappable
    }

    return ret;
}

struct SwapStep
{
    int x1;
    int y1;
    int x2;
    int y2;
};

struct DfsResult
{
    Board final_board;
    std::vector<SwapStep> steps;

    // inferred fields
    int final_board_locks;
    std::array<int, 6> final_board_locks_per_grid_type;
    bool final_board_has_stun;
};

class ResultComparator
{
public:
    static void FillDfsResult(DfsResult &result, const GridParser &grid_parser)
    {
        result.final_board_locks = 0;
        for (int &v : result.final_board_locks_per_grid_type)
        {
            v = 0;
        }

        for (int x = 0; x < 7; ++x)
        {
            for (int y = 0; y < 5; ++y)
            {
                if (result.final_board.locked_[x][y])
                {
                    result.final_board_locks++;
                    result.final_board_locks_per_grid_type[result.final_board.grids_[x][y]]++;
                }
            }
        }

        result.final_board_has_stun = has_stun(result.final_board);
    }

    bool operator()(const DfsResult &lhs, const DfsResult &rhs)
    {
        if (lhs.final_board_has_stun)
            return true;
        if (rhs.final_board_has_stun)
            return false;

        // prefer blues=0, purples=2
        const int lhs_blue_count = lhs.final_board_locks_per_grid_type[2];
        const int rhs_blue_count = rhs.final_board_locks_per_grid_type[2];
        if (lhs_blue_count > rhs_blue_count)
            return true;
        if (rhs_blue_count > lhs_blue_count)
            return false;

        if (lhs.final_board_locks > rhs.final_board_locks)
            return true;
        if (rhs.final_board_locks > lhs.final_board_locks)
            return false;

        return lhs.steps.size() < rhs.steps.size();
    }

private:
    static bool has_stun(const Board &board)
    {
        for (int y = 0; y < 5; ++y)
        {
            bool all_same = true;
            for (int x = 1; x < 7; ++x)
            {
                if (board.grids_[x][y] != board.grids_[x - 1][y])
                {
                    all_same = false;
                    break;
                }
            }
            if (all_same)
                return true;
        }
        return false;
    }
};

class BoardDfsWalker
{
public:
    BoardDfsWalker(const GridParser &grid_parser) : grid_parser_{grid_parser}
    {
        swappable_directions_.push_back({0, 1});
        swappable_directions_.push_back({1, -1});
        swappable_directions_.push_back({1, 0});
        swappable_directions_.push_back({1, 1});
    }

    std::vector<DfsResult> dfs(const Board &board)
    {
        results_.clear();
        visited_.clear();

        internal_dfs(board, {});

        return results_;
    }

private:
    void internal_dfs(const Board &board, const std::vector<SwapStep> &steps)
    {
        const auto [it, inserted] = visited_.insert(board.grids_);
        if (!inserted)
        {
            return; // already visited
        }

        // early-exit
        if (this->results_.size() > 1000) return;

        bool any_swappable = false;
        for (int x = 0; x < 7; ++x)
        {
            for (int y = 0; y < 5; ++y)
            {
                for (const auto &dir : swappable_directions_)
                {
                    const auto swapped = board.swap(x, y, x + dir.first, y + dir.second);
                    if (!swapped.has_value())
                    {
                        continue;
                    }

                    any_swappable = true;

                    auto new_steps = steps;
                    new_steps.push_back(SwapStep{x, y, x + dir.first, y + dir.second});
                    internal_dfs(*swapped, new_steps);
                }
            }
        }

        if (!any_swappable)
        {
            DfsResult result;
            result.final_board = board;
            result.steps = steps;
            ResultComparator::FillDfsResult(result, grid_parser_);
            results_.push_back(result);
        }
    }

private:
    const GridParser &grid_parser_;
    std::vector<PointT> swappable_directions_;

    std::unordered_set<BoardArrayT<int>> visited_;
    std::vector<DfsResult> results_;
};

int main(int argc, char *argv[])
{
    GridParser grid_parser;

    std::istreambuf_iterator<char> begin(std::cin), end;
    std::string s(begin, end);

    Board board;
    board.parse(s, grid_parser);
    board.update_locks();

    BoardDfsWalker dfs{grid_parser};
    auto results = dfs.dfs(board);

    ResultComparator comparator;
    const auto it = std::min_element(
        results.begin(),
        results.end(),
        comparator);

    for (const auto& step : it->steps) {
        std::cout << step.x1 << " " << step.y1 << " " << step.x2 << " " << step.y2 << std::endl;
    }

    return 0;
}
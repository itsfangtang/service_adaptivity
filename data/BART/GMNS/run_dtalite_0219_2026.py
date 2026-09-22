import pandas as pd
import DTALite as dta
import os

# Change to the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)


def fill_zone_id_from_physical_stop_no(node_file='node.csv'):
    """
    Step 1: In node.csv, check if zone_id is empty. If empty, fill zone_id with
    values from physical_stop_no and save the file.

    Parameters:
    - node_file: str, path to the node CSV file.
    """
    node_df = pd.read_csv(node_file)

    if 'zone_id' not in node_df.columns or 'physical_stop_no' not in node_df.columns:
        raise ValueError(f"{node_file} must contain both 'zone_id' and 'physical_stop_no' columns.")

    # Treat as empty: NaN or empty string
    empty_mask = node_df['zone_id'].isna() | (node_df['zone_id'].astype(str).str.strip() == '')
    n_empty = empty_mask.sum()

    if n_empty > 0:
        print(f"Step 1: {node_file} has {n_empty} row(s) with empty zone_id. Filling from physical_stop_no.")
        node_df.loc[empty_mask, 'zone_id'] = node_df.loc[empty_mask, 'physical_stop_no']
        node_df.to_csv(node_file, index=False)
    else:
        print(f"Step 1: {node_file} zone_id column has no empty values, no change needed.")


def renumber_and_sort_node_id(node_file='node.csv', link_file='link.csv'):
    """
    Step 2: Rename node_id to old_node_id, create new node_id column to its left.
    Rows with zone_id get node_id 1, 2, 3, ...; rows without zone_id get 1001, 1002, ...
    Sort by new node_id. Update link.csv from_node_id/to_node_id to use new node_id.
    """
    node_df = pd.read_csv(node_file)

    if 'node_id' not in node_df.columns:
        raise ValueError(f"{node_file} must contain 'node_id' column.")
    if 'zone_id' not in node_df.columns:
        raise ValueError(f"{node_file} must contain 'zone_id' column.")

    # Rename node_id to old_node_id only if old_node_id does not already exist
    # (e.g. file was already processed by a previous run)
    if 'old_node_id' not in node_df.columns:
        node_df = node_df.rename(columns={'node_id': 'old_node_id'})
    else:
        node_df = node_df.drop(columns=['node_id'], errors='ignore')

    # Empty zone_id: NaN or blank string
    has_zone = ~node_df['zone_id'].isna() & (node_df['zone_id'].astype(str).str.strip() != '')
    n_zone = has_zone.sum()

    # Sort: zone nodes first (ascending old_node_id), then non-zone (ascending old_node_id)
    node_df['_zone_first'] = (~has_zone).astype(int)  # 0 = has zone, 1 = no zone → zone rows first
    node_df = node_df.sort_values(by=['_zone_first', 'old_node_id']).reset_index(drop=True)
    node_df = node_df.drop(columns=['_zone_first'])

    # Assign new node_id: 1,2,... for has_zone; 1001,1002,... for no zone
    n_zone = has_zone.sum()
    new_ids = list(range(1, n_zone + 1)) + list(range(1001, 1001 + (len(node_df) - n_zone)))
    node_df.insert(node_df.columns.get_loc('old_node_id'), 'node_id', new_ids)

    node_df.to_csv(node_file, index=False)
    print(f"Step 2: Renumbered and sorted {node_file}: {n_zone} zone nodes (1–{n_zone}), {len(node_df) - n_zone} non-zone (1001+).")


def link_node_id_vlookup(node_file='node.csv', link_file='link.csv'):
    """
    Step 4: In link.csv, rename from_node_id/to_node_id to old_from_node_id/old_to_node_id,
    create new from_node_id and to_node_id to their left, and fill them by Vlookup against
    node.csv (match old_from_node_id/old_to_node_id to old_node_id, use node_id).
    """
    node_df = pd.read_csv(node_file)
    if 'old_node_id' not in node_df.columns or 'node_id' not in node_df.columns:
        raise ValueError(f"{node_file} must contain 'old_node_id' and 'node_id' columns.")

    # Build old_node_id -> node_id (int keys so CSV float ids match)
    old_to_new = {
        int(k): v
        for k, v in zip(node_df['old_node_id'], node_df['node_id'])
        if pd.notna(k)
    }

    def _map_id(x):
        if pd.isna(x) or x == '':
            return pd.NA
        try:
            return old_to_new.get(int(float(x)))
        except (ValueError, TypeError):
            return pd.NA

    link_df = pd.read_csv(link_file)

    # Rename existing from_node_id / to_node_id to old_* if not already present
    if 'old_from_node_id' not in link_df.columns and 'from_node_id' in link_df.columns:
        link_df = link_df.rename(columns={'from_node_id': 'old_from_node_id'})
    if 'old_to_node_id' not in link_df.columns and 'to_node_id' in link_df.columns:
        link_df = link_df.rename(columns={'to_node_id': 'old_to_node_id'})

    if 'old_from_node_id' not in link_df.columns or 'old_to_node_id' not in link_df.columns:
        print("Step 4: link.csv has no old_from_node_id/old_to_node_id, skipped.")
        return

    # Create from_node_id to the left of old_from_node_id and fill by Vlookup
    if 'from_node_id' not in link_df.columns:
        new_from = link_df['old_from_node_id'].apply(_map_id)
        link_df.insert(link_df.columns.get_loc('old_from_node_id'), 'from_node_id', new_from)
    else:
        link_df['from_node_id'] = link_df['old_from_node_id'].apply(_map_id)

    # Create to_node_id to the left of old_to_node_id and fill by Vlookup
    if 'to_node_id' not in link_df.columns:
        new_to = link_df['old_to_node_id'].apply(_map_id)
        link_df.insert(link_df.columns.get_loc('old_to_node_id'), 'to_node_id', new_to)
    else:
        link_df['to_node_id'] = link_df['old_to_node_id'].apply(_map_id)

    link_df.to_csv(link_file, index=False)
    print("Step 4: link.csv now has old_from_node_id/old_to_node_id; from_node_id/to_node_id filled by Vlookup from node.csv.")


def renumber_and_sort_link_id(link_file='link.csv'):
    """
    Step 3: Rename link_id to old_link_id, create new link_id column to its left.
    Sort by from_node_id, to_node_id, then assign new link_id from 1 ascending (1, 2, 3, ...).
    """
    link_df = pd.read_csv(link_file)

    if 'link_id' not in link_df.columns:
        raise ValueError(f"{link_file} must contain 'link_id' column.")

    link_df = link_df.rename(columns={'link_id': 'old_link_id'})

    # Sort by from_node_id, to_node_id for stable order
    if 'from_node_id' in link_df.columns and 'to_node_id' in link_df.columns:
        link_df = link_df.sort_values(by=['from_node_id', 'to_node_id']).reset_index(drop=True)
    else:
        link_df = link_df.reset_index(drop=True)

    new_ids = list(range(1, len(link_df) + 1))
    link_df.insert(link_df.columns.get_loc('old_link_id'), 'link_id', new_ids)

    link_df.to_csv(link_file, index=False)
    print(f"Step 3: Renumbered and sorted {link_file}: link_id 1–{len(link_df)}.")


def check_and_sort_files(node_file='node.csv', link_file='link.csv'):
    """
    Check if node_file is sorted by node_id and link_file is sorted first by
    from_node_id and then by to_node_id. If not, sort the files and save them.

    Parameters:
    - node_file: str, path to the node CSV file.
    - link_file: str, path to the link CSV file.
    """

    # Check if node.csv is sorted by node_id
    node_df = pd.read_csv(node_file)
    if not node_df['node_id'].is_monotonic_increasing:
        print(f"{node_file} is not sorted by node_id. Sorting now.")
        node_df.sort_values('node_id', inplace=True)
        node_df.to_csv(node_file, index=False)
    else:
        print(f"{node_file} is already sorted by node_id.")

    # Check if link.csv is sorted by from_node_id and to_node_id (first sort by from_node_id, then to_node_id)
    link_df = pd.read_csv(link_file)
    sorted_link_df = link_df.sort_values(by=['from_node_id', 'to_node_id']).reset_index(drop=True)
    current_link_order = link_df[['from_node_id', 'to_node_id']].reset_index(drop=True)

    if not current_link_order.equals(sorted_link_df[['from_node_id', 'to_node_id']]):
        print(f"{link_file} is not sorted by from_node_id and to_node_id. Sorting now.")
        sorted_link_df.to_csv(link_file, index=False)
    else:
        print(f"{link_file} is already sorted by from_node_id and to_node_id.")


# Pre-checks before running DTALite
fill_zone_id_from_physical_stop_no()   # Step 1: fill empty zone_id from physical_stop_no
renumber_and_sort_node_id()            # Step 2: renumber node_id, zone 1..n / non-zone 1001..
link_node_id_vlookup()                 # Step 4: link.csv: old_from/to_node_id + from/to_node_id by Vlookup
renumber_and_sort_link_id()            # Step 3: renumber link_id 1..n, sort by from_node_id, to_node_id
check_and_sort_files()                 # Sort node/link files if needed
dta.assignment()

# dta.simulation()
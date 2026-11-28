from app.services.analyst_workspace import AnalystWorkspaceStore

def test_workspace_projects_notes_watchlists_persist(tmp_path):
 p=tmp_path/"workspace.sqlite3";store=AnalystWorkspaceStore(p)
 project=store.create_project("user-1","Weekend research","Review")
 store.add_note(project["project_id"],"Fixture note","Investigate lineup update",["ev-1"])
 store.add_watchlist_item(project["project_id"],"event:ev-1","event","Home v Away")
 reopened=AnalystWorkspaceStore(p)
 assert reopened.list_projects("user-1")[0]["project_id"]==project["project_id"]
 assert reopened.list_notes(project["project_id"])[0]["evidence_ids"]==["ev-1"]
 assert reopened.list_watchlist(project["project_id"])[0]["item_key"]=="event:ev-1"
